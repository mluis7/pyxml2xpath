import glob
from xml2xpath import xml2xpath

class TestPyXml2Xpath01:
    def test_all_samples_basic(self):
        sample_paths = glob.glob('resources/*.xml')
        xpath_base = "//*"
        print("")
        for xfile in sample_paths:
            print(f"Testing '{xfile}'")
            xmap = xml2xpath.parse(xfile,  xpath_base=xpath_base)[2]
            print(f"    --> Found {len(xmap.keys())} xpath expressions")
            assert len(xmap.keys()) > 0
            # assert all found expressions exist at least once in the document.
            assert len([v for v in xmap.values() if v[1] == 0]) == 0
    
    def test_parse_with_initial_xpath(self):
        filepath = 'resources/soap.xml'
        xpath_base = '//*[local-name()="incident"]'
        print(f"\nTesting '{filepath}' starting at: '{xpath_base}'")
        
        xmap = xml2xpath.parse(filepath,  xpath_base=xpath_base)[2]
        print(f"    --> Found {len(xmap.keys())} xpath expressions")
        # do not count parent element
        assert len([k for k in xmap if k != '/soap:Envelope/soap:Body' ]) == 1
        # assert all found expressions exist at least once in the document.
        assert len([v for v in xmap.values() if v[1] == 0]) == 0
