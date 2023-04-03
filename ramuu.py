"""Script to summarize RAM prices."""

import collections
import datetime
import decimal
import json
import statistics
import unittest

class Item:
    def __init__(self, date, dimm_type, store, count, size, price, brand):
        """Initialize an Item instance."""
        if not isinstance(date, datetime.date):
            raise TypeError('date must be a datetime.date.')
        if not isinstance(dimm_type, str):
            raise TypeError('dimm_type must be a non-empty string.')
        if len(dimm_type) < 6:
            raise ValueError('dimm_type must be a non-empty string.')
        if not isinstance(store, str):
            raise TypeError('store must be a non-empty string.')
        if len(store) < 5:
            raise ValueError('store must be a non-empty string.')
        if not isinstance(count, int):
            raise TypeError('count must be a positive integer.')
        if count <= 0:
            raise ValueError('count must be a positive integer.')
        if not isinstance(size, int):
            raise TypeError('size must be a positive integer.')
        if size <= 0:
            raise ValueError('size must be a positive integer.')
        if not isinstance(price, decimal.Decimal):
            raise TypeError('price must be a decimal.Decimal.')
        if not isinstance(brand, str):
            raise TypeError('brand must be a non-empty string.')
        if len(brand) < 3:
            raise ValueError('brand must be a non-empty string.')

        self.date = date
        """datetime.date the price was collected."""

        self.dimm_type = dimm_type.strip().lower()
        """String type of the RAM module."""

        self.store = store.strip().lower()
        """String name of the store selling this item."""

        self.count = count
        """Integer number of modules in this item."""

        self.size = size
        """Integer size in GB of each RAM module."""

        self.price = price
        """decimal.Decimal price on self.date."""

        self.brand = brand.strip().lower()
        """String brand of the manufacturer."""

    def __str__(self):
        return '{}x{}GB@${} {} for {} from {} on {}'.format(
            self.count, self.size, self.price, self.brand,
            self.dimm_type, self.store, self.date.isoformat())

    @property
    def total_size(self):
        """Return the integer total size in GB of this item."""
        return self.count * self.size


def _parse_description(description):
    """Return the count, the size, the price, and the brand from description.

    Args:
        description: String description in the form "2x8GB@$19.99 Brand".
    Returns:
        Integer module count
        Integer module size in GB
        decimal.Decimal price
        String brand
    """
    if not isinstance(description, str):
        raise TypeError('description must be a non-empty string.')
    if len(description) < 10:
        raise ValueError('description must be a non-empty string.')

    x_index = description.find('x')
    dollar_index = description.find('GB@$')
    space_index = description.find(' ')

    if x_index <= 0:
        count = 1
    else:
        count = int(description[:x_index])

    size = 0
    price = decimal.Decimal()
    brand = ''
    if space_index > 0:
        brand = description[space_index+1:]
        if dollar_index > 0:
            size = int(description[x_index+1:dollar_index])
            price = decimal.Decimal(description[dollar_index+4:space_index])

    return count, size, price, brand

def _parse_module_size(description):
    """Return a string size of the memory module in description.

    >>> _parse_module_size('4GB')
    '4'
    >>> _parse_module_size('8 GB')
    '8'
    >>> _parse_module_size('16GB (2x8GB)')
    '2x8'
    >>> _parse_module_size('(2 x 8GB) 16GB')
    '2x8'

    Args:
        description: String description of a RAM module.
    Returns:
        String size of the memory module in description.
    """
    if not isinstance(description, str):
        raise TypeError('description must be a string.')

    sizes = []
    end = -1
    while True:
        end = description.find('GB', end + 1)
        if end <= 0:
            break
        start = end - 1
        # Skip any space between the size and "GB"
        while (start >= 0) and description[start].isspace():
            start -= 1
        # Move to the start of the size
        while (start >= 0) and description[start].isdigit():
            start -= 1
        start += 1
        try:
            sizes.append(int(description[start:end].strip()))
        except ValueError:
            pass

    if len(sizes) <= 0:
        return None
    if len(sizes) == 1:
        return str(sizes[0])
    else:
        if sizes[0] == sizes[1]:
            return str(sizes[0])
        else:
            numerator = max(*sizes[:2])
            denominator = min(*sizes[:2])
            return '{}x{}'.format(numerator // denominator, denominator)

def _parse_micro_center(source):
    """Parse and print the micro center webpage in source.

    Args:
        source: String source of the micro center webpage.
    Returns:
        List of float price and string description tuples.
    """
    if not isinstance(source, str):
        raise TypeError('source must be a string.')

    start = source.find('<div id="productImpressions" class="hidden">')
    end = source.find('</div>', start + 44)
    products = json.loads('[' + source[start+44:end].replace("'", '"') + ']')
    if not isinstance(products, list):
        return []

    descriptions = []
    for product in products:
        if not isinstance(product, dict):
            continue
        size = _parse_module_size(product.get('name'))
        if not isinstance(size, str):
            continue
        price = product.get('price')
        size += 'GB@${} {}'.format(price, product.get('brand'))
        # Add price as the first element of the tuple for sorting
        descriptions.append((decimal.Decimal(price.replace(',', '')), size))

    if len(descriptions) > 0:
        print('        micro center:')
        descriptions.sort()
        for price, description in descriptions:
            print('        -', description)

    return descriptions

def _parse_newegg(source):
    """Parse and print the titles in the Newegg feed in source.

    Args:
        source: String source of the Newegg feed.
    Returns:
        List of float price and string description tuples.
    """
    if not isinstance(source, str):
        raise TypeError('source must be a string.')

    descriptions = []
    start = -1
    while True:
        start = source.find('<title>', start + 1)
        if start <= 0:
            break
        end = source.find('</title>', start + 7)
        title = source[start+7:end].strip()
        if not title.startswith('&#36;'):
            continue

        title = title[5:]
        size = _parse_module_size(title)
        if not isinstance(size, str):
            continue
        separator = title.find(' - ')
        price = title[:separator]
        brand_end = separator + 3
        while not title[brand_end].isspace():
            brand_end += 1
        brand = title[separator+3:brand_end].strip()
        size += 'GB@${} {}'.format(price, brand)
        # Add price as the first element of the tuple for sorting
        descriptions.append((decimal.Decimal(price.replace(',', '')), size))

    if len(descriptions) > 0:
        print('        Newegg:')
        descriptions.sort()
        for price, description in descriptions:
            print('        -', description)

    return descriptions

def _parse_document(document):
    """Return a dictionary of Item instances parsed from document.

    Args:
        document: Dictionary containing price descriptions.
    Returns:
        Dictionary mapping a datetime.date to a list of Item instances.
    """
    if not isinstance(document, dict):
        return {}

    result = collections.defaultdict(list)
    for date in document:
        if not isinstance(date, datetime.date):
            continue
        if not isinstance(document[date], dict):
            continue
        for dimm_type in document[date]:
            if not isinstance(document[date][dimm_type], dict):
                continue
            for store in document[date][dimm_type]:
                if not isinstance(document[date][dimm_type][store], list):
                    continue
                for entry in document[date][dimm_type][store]:
                    count, size, price, brand = _parse_description(entry)
                    if size > 0:
                        try:
                            result[date].append(
                                Item(date, dimm_type, store, count,
                                     size, price, brand))
                        except ValueError:
                            print('Invalid entry:', entry)
    return result


class _UnitTest(unittest.TestCase):
    def test_parse_description(self):
        """Test parsing the string description."""
        for value in [None, 42.0, []]:
            self.assertRaises(TypeError, _parse_description, value)
        for value in ['', 'foobar', 'foobarbaz']:
            self.assertRaises(ValueError, _parse_description, value)
        for value, expected in [
            ('4GB@$14.99', (1, 0, decimal.Decimal(), '')),
            ('4GB@$14.99 ', (1, 4, decimal.Decimal('14.99'), '')),
            ('4GB@$14.99 Foo', (1, 4, decimal.Decimal('14.99'), 'Foo')),
            ('8GB@$18.99', (1, 0, decimal.Decimal(), '')),
            ('8GB@$18.99 ', (1, 8, decimal.Decimal('18.99'), '')),
            ('8GB@$18.99 Foo', (1, 8, decimal.Decimal('18.99'), 'Foo')),
            ('1x4GB@$14.99', (1, 0, decimal.Decimal(), '')),
            ('1x4GB@$14.99 ', (1, 4, decimal.Decimal('14.99'), '')),
            ('1x4GB@$14.99 Foo', (1, 4, decimal.Decimal('14.99'), 'Foo')),
            ('1x8GB@$18.99', (1, 0, decimal.Decimal(), '')),
            ('1x8GB@$18.99 ', (1, 8, decimal.Decimal('18.99'), '')),
            ('1x8GB@$18.99 Foo', (1, 8, decimal.Decimal('18.99'), 'Foo')),
            ('2x4GB@$24.99', (2, 0, decimal.Decimal(), '')),
            ('2x4GB@$24.99 ', (2, 4, decimal.Decimal('24.99'), '')),
            ('2x4GB@$24.99 Foo', (2, 4, decimal.Decimal('24.99'), 'Foo')),
            ('2x8GB@$28.99', (2, 0, decimal.Decimal(), '')),
            ('2x8GB@$28.99 ', (2, 8, decimal.Decimal('28.99'), '')),
            ('2x8GB@$28.99 Foo', (2, 8, decimal.Decimal('28.99'), 'Foo')),
            ('4x4GB@$44.99', (4, 0, decimal.Decimal(), '')),
            ('4x4GB@$44.99 ', (4, 4, decimal.Decimal('44.99'), '')),
            ('4x4GB@$44.99 Foo', (4, 4, decimal.Decimal('44.99'), 'Foo')),
            ('4x8GB@$48.99', (4, 0, decimal.Decimal(), '')),
            ('4x8GB@$48.99 ', (4, 8, decimal.Decimal('48.99'), '')),
            ('4x8GB@$48.99 Foo', (4, 8, decimal.Decimal('48.99'), 'Foo')),
            ('10x1GB@$101.99', (10, 0, decimal.Decimal(), '')),
            ('10x1GB@$101.99 ', (10, 1, decimal.Decimal('101.99'), '')),
            ('10x1GB@$101.99 Foo', (10, 1, decimal.Decimal('101.99'), 'Foo'))]:
            self.assertEqual(_parse_description(value), expected)

    def test_parse_module_size(self):
        """Test parsing a memory module's size."""
        for value in [None, 42.0, []]:
            self.assertRaises(TypeError, _parse_module_size, value)
        for value in ['', 'foobar', 'foobarbaz']:
            self.assertIsNone(_parse_module_size(value))
        for value, expected in [
            (' 4GB', '4'),
            (' 4 GB', '4'),
            ('8GB', '8'),
            ('8 GB', '8'),
            ('16GB ', '16'),
            ('16 GB ', '16'),
            ('16GB (2x8GB)', '2x8'),
            ('16GB (2x 8GB)', '2x8'),
            ('16GB (2x8 GB)', '2x8'),
            ('16GB (2x 8 GB)', '2x8'),
            ('16GB (2 x8GB)', '2x8'),
            ('16GB (2 x 8GB)', '2x8'),
            ('16GB (2 x8 GB)', '2x8'),
            ('16GB (2 x 8 GB)', '2x8'),
            ('16 GB (2x8GB)', '2x8'),
            ('16 GB (2x 8GB)', '2x8'),
            ('16 GB (2x8 GB)', '2x8'),
            ('16 GB (2x 8 GB)', '2x8'),
            ('16 GB (2 x8GB)', '2x8'),
            ('16 GB (2 x 8GB)', '2x8'),
            ('16 GB (2 x8 GB)', '2x8'),
            ('16 GB (2 x 8 GB)', '2x8'),
            ('(2x8GB) 16GB', '2x8'),
            ('(2x 8GB) 16GB', '2x8'),
            ('(2x8 GB) 16GB', '2x8'),
            ('(2x 8 GB) 16GB', '2x8'),
            ('(2 x8GB) 16GB', '2x8'),
            ('(2 x 8GB) 16GB', '2x8'),
            ('(2 x8 GB) 16GB', '2x8'),
            ('(2 x 8 GB) 16GB', '2x8'),
            ('(2x8GB) 16 GB', '2x8'),
            ('(2x 8GB) 16 GB', '2x8'),
            ('(2x8 GB) 16 GB', '2x8'),
            ('(2x 8 GB) 16 GB', '2x8'),
            ('(2 x8GB) 16 GB', '2x8'),
            ('(2 x 8GB) 16 GB', '2x8'),
            ('(2 x8 GB) 16 GB', '2x8'),
            ('(2 x 8 GB) 16 GB', '2x8'),
            # Test misleading numbers preceding the size
            ('4 8GB', '8'),
            ('4 8 GB', '8'),
            ('4 16GB (2x8GB)', '2x8'),
            ('4 16GB (2x 8GB)', '2x8'),
            ('4 16GB (2 x 8GB)', '2x8'),
            ('4 16GB (2 x 8 GB)', '2x8'),
            ('4 16 GB (2x8GB)', '2x8'),
            ('4 16 GB (2x 8GB)', '2x8'),
            ('4 16 GB (2 x 8GB)', '2x8'),
            ('4 16 GB (2 x 8 GB)', '2x8')]:
            self.assertEqual(_parse_module_size(value), expected)
            self.assertEqual(_parse_module_size('Foobar ' + value), expected)
            self.assertEqual(_parse_module_size(value + ' baz'), expected)
            self.assertEqual(_parse_module_size('Foobar ' + value + ' baz'),
                             expected)
            if '(' in value:
                self.assertEqual(_parse_module_size(value.replace('(', '( ')),
                                 expected)
                self.assertEqual(_parse_module_size(value.replace(')', ' )')),
                                 expected)

    def test_parse_micro_center(self):
        """Test parsing the micro center webpage."""
        for value in [None, 42.0, []]:
            self.assertRaises(TypeError, _parse_micro_center, value)
        for value in ['', 'foobar', 'foobarbaz']:
            self.assertEqual(_parse_micro_center(value), [])
        self.assertEqual(_parse_micro_center('''
<div id="productImpressions" class="hidden">{
'name': 'Foobar 4GB',
'brand': 'Foobar',
'price': '14.99'}, {
'name': 'Foobar 8GB (2 x 4GB)',
'brand': 'Foobar',
'price': '24.99'}, {
'name': 'Foobar 8GB',
'brand': 'Foobar',
'price': '18.99'}, {
'name': 'Foobar 16GB (2 x 8GB)',
'brand': 'Foobar',
'price': '28.99'}
</div>
'''), [(decimal.Decimal('14.99'), '4GB@$14.99 Foobar'),
       (decimal.Decimal('18.99'), '8GB@$18.99 Foobar'),
       (decimal.Decimal('24.99'), '2x4GB@$24.99 Foobar'),
       (decimal.Decimal('28.99'), '2x8GB@$28.99 Foobar')])

    def test_parse_newegg(self):
        """Test parsing the Newegg feed."""
        for value in [None, 42.0, []]:
            self.assertRaises(TypeError, _parse_newegg, value)
        for value in ['', 'foobar', 'foobarbaz']:
            self.assertEqual(_parse_newegg(value), [])
        self.assertEqual(_parse_newegg('''<rss version="2.0">
<title>&#36;14.99 - Foobar 4GB</title>
<title>&#36;24.99 - Foobar 8GB (2 x 4GB)</title>
<title>&#36;18.99 - Foobar 8GB</title>
<title>&#36;28.99 - Foobar 16GB (2 x 8GB)</title>
</rss>
'''), [(decimal.Decimal('14.99'), '4GB@$14.99 Foobar'),
       (decimal.Decimal('18.99'), '8GB@$18.99 Foobar'),
       (decimal.Decimal('24.99'), '2x4GB@$24.99 Foobar'),
       (decimal.Decimal('28.99'), '2x8GB@$28.99 Foobar')])

    def test_item(self):
        """Test the Item class."""
        today = datetime.datetime.now(datetime.timezone.utc).date()
        for value in [None, 42.0, []]:
            self.assertRaises(
                TypeError, Item, value, 'desktop', 'store', 1, 2,
                decimal.Decimal(), 'brand')
            self.assertRaises(
                TypeError, Item, today, value, 'store', 1, 2,
                decimal.Decimal(), 'brand')
            self.assertRaises(
                TypeError, Item, today, 'desktop', value, 1, 2,
                decimal.Decimal(), 'brand')
            self.assertRaises(
                TypeError, Item, today, 'desktop', 'store', value, 2,
                decimal.Decimal(), 'brand')
            self.assertRaises(
                TypeError, Item, today, 'desktop', 'store', 1, value,
                decimal.Decimal(), 'brand')
            self.assertRaises(
                TypeError, Item, today, 'desktop', 'store', 1, 2,
                value, 'brand')
            self.assertRaises(
                TypeError, Item, today, 'desktop', 'store', 1, 2,
                decimal.Decimal(), value)
        for value in [-1, 0]:
            self.assertRaises(
                ValueError, Item, today, 'laptop', 'store', value, 2,
                decimal.Decimal(), 'brand')
            self.assertRaises(
                ValueError, Item, today, 'laptop', 'store', 1, value,
                decimal.Decimal(), 'brand')

    def test_parse_document(self):
        """Test parsing a YAML document."""
        for value in [None, 42.0, [], {}, {'foo': 'bar'}]:
            self.assertEqual(_parse_document(value), {})

        today = datetime.datetime.now(datetime.timezone.utc).date()
        result = _parse_document({
            today: {
                'desktop': {
                    'store': ['4GB@$14.99 Foo']
                },
                'laptop': {
                    'store': ['2x4GB@$24.99 Foo']
                }
            }
        })
        self.assertEqual(len(result), 1)
        self.assertIn(today, result)
        self.assertEqual(len(result[today]), 2)

if __name__ == '__main__':
    import argparse
    import doctest
    import os.path
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '-c', '--microcenter', default=[], nargs='+',
        help='fetch, parse, and print the micro center pages at URLs')
    parser.add_argument(
        '-n', '--newegg', default=[], nargs='+',
        help='fetch, parse, and print the Newegg feeds at URLs')
    parser.add_argument(
        '-p', '--path', default='',
        help='parse the YAML price data at path')
    parser.add_argument(
        '-m', '--module', type=int, default=0,
        help='integer size of the module on which to filter')
    parser.add_argument(
        '-s', '--store', default='',
        help='string name of the store on which to filter')
    parser.add_argument(
        '-t', '--type', default='',
        help='string type of the module on which to filter')
    args = parser.parse_args()

    if len(args.microcenter) > 0:
        import requests
        with requests.Session() as session:
            for url in args.microcenter:
                response = session.get(url)
                _parse_micro_center(response.text)
    elif len(args.newegg) > 0:
        import requests
        with requests.Session() as session:
            for url in args.newegg:
                response = session.get(url)
                _parse_newegg(response.text)
    elif os.path.isfile(args.path):
        import yaml
        date_map = {}
        with open(args.path, 'r', encoding='utf-8') as f:
            for document in yaml.safe_load_all(f):
                date_map.update(_parse_document(document))
        for date in sorted(date_map.keys()):
            items = date_map[date]
            if args.module > 0:
                items = [item for item in items if item.size == args.module]
            if len(args.store) > 0:
                items = [item for item in items
                         if item.store == args.store.strip().lower()]
            if len(args.type) > 0:
                items = [item for item in items
                         if item.dimm_type == args.type.strip().lower()]
            if len(items) <= 0:
                continue
            if args.module > 0:
                print('{}: Price/Module: ${}'.format(
                    date.isoformat(), statistics.mean(
                        [item.price / item.count for item in items])))
            else:
                print('{}: Price/GB: ${}'.format(
                    date.isoformat(), statistics.mean(
                        [item.price / item.total_size for item in items])))
    else:
        tests = [doctest.DocTestSuite(),
                 unittest.defaultTestLoader.loadTestsFromTestCase(_UnitTest)]
        unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(tests))
