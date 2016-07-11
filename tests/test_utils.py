from server import utils

import datetime as dt
import pytz

from tests import OkTestCase

class TestUtils(OkTestCase):
    def test_hashids(self):
        """Tests converting hashes in URLs to IDs. Do not change the values in
        this test.
        """
        assert utils.encode_id(314159) == 'aAPZ9j'
        assert utils.decode_id('aAPZ9j') == 314159
        assert utils.encode_id(11235) == 'b28KJe'
        assert utils.decode_id('b28KJe') == 11235
        self.assertRaises(ValueError, utils.decode_id, 'deadbeef')

    def test_chunk(self):
        three_chunks = utils.chunks(range(56), 3)
        five_chunks = utils.chunks(range(55), 5)
        five_chunks = utils.chunks(list(range(55)), 5)

        self.assertEquals(list(three_chunks),
                          [range(0, 19), range(19, 38), range(38, 56)])
        self.assertEquals([len(i) for i in five_chunks],
                          [11, 11, 11, 11, 11])
        self.assertEquals([], list(utils.chunks(list(range(21)), 0)))

        self.assertEquals([len(x) for x in utils.chunks(range(45), 13)],
                          [4, 3, 4, 3, 4, 3, 4, 3, 4, 3, 4, 3, 3])
        self.assertEquals([len(x) for x in utils.chunks(range(253), 13)],
                          [20, 19, 20, 19, 20, 19, 20, 19, 20, 19, 20, 19, 19])

    def test_time(self):
        self.setup_course()
        # UTC Time
        time = dt.datetime(month=1, day=20, year=2016, hour=12, minute=1)
        self.assertEquals(utils.local_time(time, self.course), 'Wed 01/20 04:01 AM')

        # DT Aware
        pacific = pytz.timezone('US/Pacific')
        localized = pacific.localize(time)
        self.assertEquals(utils.local_time(localized, self.course), 'Wed 01/20 12:01 PM')

        eastern = pytz.timezone('US/Eastern')
        localized = eastern.localize(time)
        self.assertEquals(utils.local_time(localized, self.course), 'Wed 01/20 09:01 AM')

