import datetime
from flask import url_for
import pygal
import server.highlight as highlight

def get_unique_backups(backups):
    """
    Given a list of backups, only include backups that have changed.
    Returns a list of (backup, lines_changed) tuples
    Can assume that for every returned backup:
        - a .files() section exists
        - diff between backup_i and backup_i+1 exists
    TODO: should cache this?
    """
    filtered = []
    for i in range(len(backups)):
        # edge case for first backup
        if not i and backups[i] and backups[i].files():
            filtered.append((backups[i], -1))
            continue

        prev_backup, curr_backup = backups[i - 1], backups[i]
        prev_code, curr_code = prev_backup.files(), curr_backup.files()

        # ensure code exists
        if not (prev_code and curr_code):
            continue

        # only keep with diffs
        lines_changed = highlight.diff_lines(prev_code, curr_code)
        if lines_changed:
            filtered.append((curr_backup, lines_changed))
    return filtered

def get_time_diff_seconds(analytics1, analytics2):
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

def get_graph_stats(backups):
    """
    Given a list of backups, return a list of statistics for the unique ones
    The len(list) should be 1 less than the number of unique usuable backups
    """
    unique_backups_tuples = get_unique_backups(backups) # should be cached

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
        diff_in_secs = get_time_diff_seconds(prev_analytics, curr_analytics)
        if diff_in_secs == None or diff_in_secs < 0:
            continue

        diff_in_mins = diff_in_secs // 60 + 1 # round up

        # get ratio between curr_lines_changed and diff_in_mins
        lines_time_ratio = curr_lines_changed / diff_in_mins

        stats = {
            'submitter': curr_backup.submitter.email,
            'commit_id' : curr_backup.hashid,
            'lines_changed': curr_lines_changed,
            'diff_in_secs': diff_in_secs,
            'diff_in_mins': diff_in_mins,
            'lines_time_ratio': lines_time_ratio
        }
        stats_list.append(stats)
    return stats_list

def get_graph_points(backups, cid, email, aid, extra):
    """
    Given a list of backups, forms the points needed for a pygal graph
    """
    stats_list = get_graph_stats(backups)
    def gen_point(stat):
        value = stat["lines_time_ratio"]
        lines_changed = round(stat["lines_changed"], 5)
        label = "Total Lines:{0} \n Submitter: {1} \n Commit ID: {2}\n".format(
            lines_changed, stat["submitter"], stat["commit_id"])
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

        if extra:
            url += "?student_email=" + email
        return {
            "value": value,
            "label" : label,
            "xlink": url,
            "color": color
        }
    points = [gen_point(stat) for stat in stats_list]
    return points

def generate_line_chart(backups, cid, email, aid, extra):
    points = get_graph_points(backups, cid, email, aid, extra)

    line_chart = pygal.Line(disable_xml_declaration=True,
                            human_readable=True,
                            legend_at_bottom=True,
                            pretty_print=True
                            )
    line_chart.title = 'Lines/Minutes Ratio Across Backups'
    line_chart.add('Backups', points)
    return line_chart