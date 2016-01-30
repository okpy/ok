from werkzeug.routing import ValidationError

from .helpers import OkTestCase

class TestURL(OkTestCase):
    def test_hashids(self):
        """Tests converting hashes in URLs to IDs. Do not change this test."""
        converter_class = self.app.url_map.converters['hashid']
        converter = converter_class(self.app.url_map)
        assert converter.to_url(314159) == 'aAPZ9j'
        assert converter.to_python('aAPZ9j') == 314159
        assert converter.to_url(11235) == 'b28KJe'
        assert converter.to_python('b28KJe') == 11235
        self.assertRaises(ValidationError, converter.to_python, 'deadbeef')
