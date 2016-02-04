from werkzeug.routing import ValidationError

from server import utils

from .helpers import OkTestCase

class TestUtils(OkTestCase):
    def test_hashids(self):
        """Tests converting hashes in URLs to IDs. Do not change the values in
        this test.
        """
        assert self.app.url_map.converters['hashid'] == utils.HashidConverter
        assert utils.encode_id(314159) == 'aAPZ9j'
        assert utils.decode_id('aAPZ9j') == 314159
        assert utils.encode_id(11235) == 'b28KJe'
        assert utils.decode_id('b28KJe') == 11235
        self.assertRaises(ValidationError, utils.decode_id, 'deadbeef')
