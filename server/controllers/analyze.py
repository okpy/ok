import datetime
from flask import url_for
import pygal
import server.highlight as highlight
from server.extensions import cache

### Common Functions ###
def _get_unique_backups(backups):
    """
    Given a list of backups, only include backups that have changed.
    Returns a list of (backup, lines_changed) tuples AND
    a map from all backup_ids to their "kept" backup_id AND
    a map from kept backup_ids to their index
    Can assume that for every returned backup:
        - a .files() section exists
        - diff between backup_i and backup_i+1 exists
    """
    filtered = []
    id_map = {} # maps all backup hashid to a kept backup's hashid
    index_map = {} # maps from all kept backups to its index
    index = 1
    first_file_found = False
    for i in range(len(backups)):
        # edge case for first backup with file
        if not first_file_found:
            if backups[i] and backups[i].files():
                filtered.append((backups[i], -1))
                last_unique_id = backups[i].hashid
                id_map[backups[i].hashid] = last_unique_id
                index_map[backups[i].hashid] = 0
                first_file_found = True
            continue

        prev_backup, curr_backup = backups[i - 1], backups[i]
        prev_code, curr_code = prev_backup.files(), curr_backup.files()

        # ensure code exists
        if not (prev_code and curr_code):
            id_map[curr_backup.hashid] = last_unique_id
            continue

        # only keep with diffs
        lines_changed = highlight.diff_lines(prev_code, curr_code)
        if lines_changed:
            filtered.append((curr_backup, lines_changed))
            last_unique_id = curr_backup.hashid
            index_map[curr_backup.hashid] = index
            index += 1
        id_map[curr_backup.hashid] = last_unique_id

    return filtered, id_map, index_map

def _get_time_diff_seconds(analytics1, analytics2):
    """
    Assumes both analytics1 and analytics2 exists.
    returns None iff a `time` field is not included in either analytics1 or analytics2
    returns integer (time diff in seconds) otherwise
    """
    time1_string, time2_string = analytics1.get("time"), analytics2.get("time")
    if not (time1_string and time2_string):
        return None
    time_format = "%Y-%m-%d %X"
    time1 = datetime.datetime.strptime(time1_string.split(".")[0], time_format)
    time2 = datetime.datetime.strptime(time2_string.split(".")[0], time_format)
    time_difference = time2 - time1
    return time_difference.total_seconds()

def sort_backups(backups):
    """
    Given a list of backups, sort by analytics time, mutating the original .
    If a certains backup has no analytics; it is dropped.
    """
    def time_key(backup):
        analytics = backup and backup.analytics()
        if analytics:
            time_string = analytics.get("time")
            time_format = "%Y-%m-%d %X"
            time = datetime.datetime.strptime(time_string.split(".")[0], time_format)
            return time
        return backup.created
    backups.sort(key=time_key)

### Diff Overview Generation ###
def _get_backup_range(backups, commit_id, bound):
    """
    Naive Implementation
    Returns a dictionary: {
        "backups": backups,
        "prev_commit_id": prev_commit_id,
        "commit_id": commit_id
        "next_commit_id": next_commit_id
    }
    backups = unique backups `bound` away from backup with `commit_id`
    prev/next_commit_id = prev/next commit_id not part of backups
    """
    unique_backups_tuples, id_map, index_map = _get_unique_backups(backups)
    unique_backups = [backup_tuple[0] for backup_tuple in unique_backups_tuples]
    # invalid commit_id
    if commit_id not in id_map:
        return {}

    # find included commit_id
    commit_id = id_map[commit_id]

    commit_index = index_map[commit_id]

    # get prev and curr ids
    prev_commit_id = unique_backups[max(0, commit_index-bound-1)].hashid
    next_commit_id = unique_backups[min(len(unique_backups)-1, commit_index+bound+1)].hashid

    unique_backups = unique_backups[max(0, commit_index-bound-1)\
                                    :min(len(unique_backups), commit_index+bound+1)]
    return {
        "backups": unique_backups,
        "prev_commit_id": prev_commit_id,
        "commit_id": commit_id,
        "next_commit_id": next_commit_id
    }

def _recent_backup_finder(backups):
    """
    Given list of backups, creates a HOF used for finding the most recent backup.
    """
    partner_index = 0
    backup_count = len(backups)
    def _get_recent_backup(current_analytics):
        """
        `current_analytics`: contains the time to find the most recent backup
        attempts to find a backup b_p such that 
            "b_p.time" is the largest possible AND
            "b_p.time" < `current_time`
        Returns backup b_p, and b_p.hashid or None if nothing is found
        """
        nonlocal partner_index
        while partner_index < backup_count:
            backup = backups[partner_index]

            analytics = backup and backup.analytics()
            if analytics:
                time_diff = _get_time_diff_seconds(analytics, current_analytics)
                if time_diff < 0: # curr_analytics - analyics < 0 => too far ahead
                    if partner_index > 0:
                        prev_backup = backups[partner_index-1]
                        return prev_backup, prev_backup.hashid
                    return None, None
            partner_index += 1
        if backup_count:
            prev_backup = backups[-1]
            return prev_backup, prev_backup.hashid
        return None, None
    return _get_recent_backup

@cache.memoize(1200)
def get_diffs(backups, commit_id, partner_backups, bound=10):
    """
    Given a list `backups`, a `commit_id`, and `bound`
    Compute the a dict containing diffs/stats of surronding the `commit_id`:
        diff_dict = {
        "stats": stats_list,
        "files": files_list,
        "partners": partner_files_list,
        "prev_commit_id": prev_commit_id,
        "commit_id": commit_id,
        "next_commit_id": next_commit_id
    }
    return {} if `commit_id` not found
    """
    backup_dict = _get_backup_range(backups, commit_id, bound)

    if not backup_dict:
        return {}

    backups = backup_dict["backups"]
    commit_id = backup_dict["commit_id"] # relevant commit_id might be different
    prev_commit_id = backup_dict["prev_commit_id"]
    next_commit_id = backup_dict["next_commit_id"]

    get_recent_backup = _recent_backup_finder(partner_backups)
    assign_files = backups[0].assignment.files
    files_list, stats_list, partner_files_list = [], [], []
    for i, backup in enumerate(backups):
        if not i: # first unique backup => no diff
            continue

        prev = backups[i - 1].files()
        curr = backup.files()
        files = highlight.diff_files(prev, curr, "short")
        files_list.append(files)

        backup_stats = {
            'submitter': backup.submitter.email,
            'commit_id' : backup.hashid,
            'partner_commit_id': None,
            'question': None,
            'time': None,
            'passed': None,
            'failed': None
        }

        analytics = backup and backup.analytics()
        grading = backup and backup.grading()

        partner_backup_files = None

        if analytics:
            backup_stats['time'] = analytics.get('time')
            partner_backup, partner_backup_id = get_recent_backup(analytics)
            backup_stats["partner_commit_id"] = partner_backup_id
            if partner_backup:
                partner_backup_files = highlight.diff_files(partner_backup.files(), curr, "short")

        if grading:
            questions = list(grading.keys())
            question = None
            passed, failed = 0, 0
            for question in questions:
                passed += grading.get(question).get('passed')
                passed += grading.get(question).get('failed')
            if len(questions) > 1:
                question = questions

            backup_stats['question'] = question
            backup_stats['passed'] = passed
            backup_stats['failed'] = failed
        else:
            unlock = backup.unlocking()
            backup_stats['question'] = "[Unlocking] " + unlock.split(">")[0]

        stats_list.append(backup_stats)
        partner_files_list.append(partner_backup_files)

    diff_dict = {
        "stats": stats_list,
        "files": files_list,
        "partners": partner_files_list,
        "prev_commit_id": prev_commit_id,
        "commit_id": commit_id,
        "next_commit_id": next_commit_id
    }
    return diff_dict

### Graph Generation ###
def _get_graph_stats(backups):
    """
    Given a list of backups, return a list of statistics for the unique ones
    The len(list) should be 1 less than the number of unique usuable backups
    """
    unique_backups_tuples = _get_unique_backups(backups)[0]
    stats_list = []
    for i in range(len(unique_backups_tuples)):
        if not i: # first unique backup => no diff
            continue

        prev_backup, curr_backup = unique_backups_tuples[i - 1][0], unique_backups_tuples[i][0]
        curr_lines_changed = unique_backups_tuples[i][1] # stored in tuple!
        prev_analytics = prev_backup and prev_backup.analytics()
        curr_analytics = curr_backup and curr_backup.analytics()

         # ensure analytics exists
        if not (prev_analytics and curr_analytics):
            continue

        # get time differences
        diff_in_secs = _get_time_diff_seconds(prev_analytics, curr_analytics)
        diff_in_mins = diff_in_secs // 60 + 1 # round up

        # get ratio between curr_lines_changed and diff_in_mins
        lines_time_ratio = curr_lines_changed / diff_in_mins
        # lines_time_ratio = curr_lines_changed / max(diff_in_mins, 1)

        # Getting timestamp and question progress from analytics
        timestamp = 'N/A'
        if curr_analytics:
            working_q = curr_analytics.get('question')
            if not working_q:
                curr_q = 'N/A'
            else:
                curr_q = working_q[0]
            timestamp = curr_analytics.get('time')


        stats = {
            'commit_id' : curr_backup.hashid,
            'lines_changed': curr_lines_changed,
            'lines_time_ratio': lines_time_ratio,
            'curr_q': curr_q,
            'timestamp': timestamp
        }
        stats_list.append(stats)
    return stats_list

def _get_graph_points(backups, cid, email, aid):
    """
    Given a list of backups, forms the points needed for a pygal graph
    """
    stats_list = _get_graph_stats(backups)
    def gen_point(stat):
        value = stat["lines_time_ratio"]
        lines_changed = round(stat["lines_changed"], 5)
        label = "Lines Changed: {0} | Commit ID: {1} | Question: {2}".format(
            lines_changed, stat["commit_id"], stat["curr_q"])
        url = url_for('.student_commit_overview', 
                cid=cid, email=email, aid=aid, commit_id=stat["commit_id"])

        #arbitrary boundaries for color-coding based on ratio, need more data to determine bounds
        if lines_changed > 100: 
            color = 'red'
        elif lines_changed > 50:
            color = 'orange'
        elif lines_changed > 15:
            color = 'blue'
        else:
            color = 'black'

        return {
            "value": value,
            "label" : label,
            "xlink": url,
            "color": color
        }
    points = [gen_point(stat) for stat in stats_list]
    timestamps = [stat['timestamp'] for stat in stats_list]
    return points, timestamps

@cache.memoize(1200)
def generate_line_chart(backups, cid, email, aid):
    """
    Generates a pygal line_chart given a list of backups
    """
    points, timestamps = _get_graph_points(backups, cid, email, aid)

    line_chart = pygal.Line(disable_xml_declaration=True,
                            human_readable=True,
                            legend_at_bottom=True,
                            pretty_print=True,
                            show_legend=False
                            )
    line_chart.title = 'Lines/Minutes Ratio Across Backups: {0}'.format(email)
    line_chart.add('Backups', points)
    line_chart.x_labels = timestamps
    return line_chart
