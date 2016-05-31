from server import utils

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

        assert list(three_chunks) == [range(0, 19),
                                      range(19, 38), range(38, 56)]
        assert [len(i) for i in five_chunks] == [11, 11, 11, 11, 11]

        assert [] == list(utils.chunks(list(range(21)), 0))

