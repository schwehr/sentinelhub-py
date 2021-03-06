"""
Utility functions to read/write image data from/to file
"""

import csv
import json
import os
import struct
import logging
import warnings
from xml.etree import ElementTree

import numpy as np
import tifffile as tiff
from PIL import Image

from .constants import MimeType
from .os_utils import create_parent_folder


warnings.simplefilter('ignore', Image.DecompressionBombWarning)
LOGGER = logging.getLogger(__name__)

CSV_DELIMITER = ';'


def read_data(filename, data_format=None):
    """ Read image data from file

    This function reads input data from file. The format of the file
    can be specified in ``data_format``. If not specified, the format is
    guessed from the extension of the filename.

    :param filename: filename to read data from
    :type filename: str
    :param data_format: format of filename. Default is `None`
    :type data_format: MimeType
    :return: data read from filename
    :raises: exception if filename does not exist
    """
    if not os.path.exists(filename):
        raise ValueError('Filename {} does not exist'.format(filename))

    if not isinstance(data_format, MimeType):
        data_format = get_data_format(filename)

    if data_format.is_tiff_format():
        return read_tiff_image(filename)
    if data_format is MimeType.JP2:
        return read_jp2_image(filename)
    if data_format.is_image_format():
        return read_image(filename)
    try:
        return {
            MimeType.TXT: read_text,
            MimeType.CSV: read_csv,
            MimeType.JSON: read_json,
            MimeType.XML: read_xml,
            MimeType.GML: read_xml,
            MimeType.SAFE: read_xml
        }[data_format](filename)
    except KeyError:
        raise ValueError('Reading data format .{} is not supported'.format(data_format.value))


def read_tiff_image(filename):
    """ Read data from TIFF file

    :param filename: name of TIFF file to be read
    :type filename: str
    :return: data stored in TIFF file
    """
    return tiff.imread(filename)


def read_jp2_image(filename):
    """ Read data from JPEG2000 file

    :param filename: name of JPEG2000 file to be read
    :type filename: str
    :return: data stored in JPEG2000 file
    """
    # Other option:
    # return glymur.Jp2k(filename)[:]
    image = read_image(filename)

    with open(filename, 'rb') as file:
        bit_depth = get_jp2_bit_depth(file)

    return fix_jp2_image(image, bit_depth)


def read_image(filename):
    """ Read data from PNG or JPG file

    :param filename: name of PNG or JPG file to be read
    :type filename: str
    :return: data stored in JPG file
    """
    return np.array(Image.open(filename))


def read_text(filename):
    """ Read data from text file

    :param filename: name of text file to be read
    :type filename: str
    :return: data stored in text file
    """
    with open(filename, 'r') as file:
        return file.read()   # file.readline() for reading 1 line


def read_csv(filename, delimiter=CSV_DELIMITER):
    """ Read data from CSV file

    :param filename: name of CSV file to be read
    :type filename: str
    :param delimiter: type of CSV delimiter. Default is ``;``
    :type delimiter: str
    :return: data stored in CSV file as list
    """
    with open(filename, 'r') as file:
        return list(csv.reader(file, delimiter=delimiter))


def read_json(filename):
    """ Read data from JSON file

    :param filename: name of JSON file to be read
    :type filename: str
    :return: data stored in JSON file
    """
    with open(filename, 'r') as file:
        return json.load(file)


def read_xml(filename):
    """ Read data from XML or GML file

    :param filename: name of XML or GML file to be read
    :type filename: str
    :return: data stored in XML file
    """
    return ElementTree.parse(filename)


def read_numpy(filename):
    """ Read data from numpy file

    :param filename: name of numpy file to be read
    :type filename: str
    :return: data stored in file as numpy array
    """
    return np.load(filename)


def write_data(filename, data, data_format=None, compress=False, add=False):
    """ Write image data to file

    Function to write image data to specified file. If file format is not provided
    explicitly, it is guessed from the filename extension. If format is TIFF, geo
    information and compression can be optionally added.

    :param filename: name of file to write data to
    :type filename: str
    :param data: image data to write to file
    :type data: numpy array
    :param data_format: format of output file. Default is `None`
    :type data_format: MimeType
    :param compress: whether to compress data or not. Default is `False`
    :type compress: bool
    :param add: whether to append to existing text file or not. Default is `False`
    :type add: bool
    :raises: exception if numpy format is not supported or file cannot be written
    """
    create_parent_folder(filename)

    if not isinstance(data_format, MimeType):
        data_format = get_data_format(filename)

    if data_format.is_tiff_format():
        return write_tiff_image(filename, data, compress)
    if data_format.is_image_format():
        return write_image(filename, data)
    if data_format is MimeType.TXT:
        return write_text(filename, data, add=add)

    try:
        return {
            MimeType.CSV: write_csv,
            MimeType.JSON: write_json,
            MimeType.XML: write_xml,
            MimeType.GML: write_xml
        }[data_format](filename, data)
    except KeyError:
        raise ValueError('Writing data format .{} is not supported'.format(data_format.value))


def write_tiff_image(filename, image, compress=False):
    """ Write image data to TIFF file

    :param filename: name of file to write data to
    :type filename: str
    :param image: image data to write to file
    :type image: numpy array
    :param compress: whether to compress data. If `True`, lzma compression is used. Default is `False`
    :type compress: bool
    """
    if compress:
        return tiff.imsave(filename, image, compress='lzma')  # loseless compression, works very well on masks
    return tiff.imsave(filename, image)


def write_jp2_image(filename, image):
    """ Write image data to JPEG2000 file

    :param filename: name of JPEG2000 file to write data to
    :type filename: str
    :param image: image data to write to file
    :type image: numpy array
    :return: jp2k object
    """
    # Other options:
    # return glymur.Jp2k(filename, data=image)
    # cv2.imwrite(filename, image)
    return write_image(filename, image)


def write_image(filename, image):
    """ Write image data to PNG, JPG file

    :param filename: name of PNG or JPG file to write data to
    :type filename: str
    :param image: image data to write to file
    :type image: numpy array
    """
    data_format = get_data_format(filename)
    if data_format is MimeType.JPG:
        LOGGER.warning('Warning: jpeg is a lossy format therefore saved data will be modified.')
    return Image.fromarray(image).save(filename)


def write_text(filename, data, add=False):
    """ Write image data to text file

    :param filename: name of text file to write data to
    :type filename: str
    :param data: image data to write to text file
    :type data: numpy array
    :param add: whether to append to existing file or not. Default is `False`
    :type add: bool
    """
    write_type = 'a' if add else 'w'
    with open(filename, write_type) as file:
        print(data, end='', file=file)


def write_csv(filename, data, delimiter=CSV_DELIMITER):
    """ Write image data to CSV file

    :param filename: name of CSV file to write data to
    :type filename: str
    :param data: image data to write to CSV file
    :type data: numpy array
    :param delimiter: delimiter used in CSV file. Default is ``;``
    :type delimiter: str
    """
    with open(filename, 'w') as file:
        csv_writer = csv.writer(file, delimiter=delimiter)
        for line in data:
            csv_writer.writerow(line)


def write_json(filename, data):
    """ Write data to JSON file

    :param filename: name of JSON file to write data to
    :type filename: str
    :param data: data to write to JSON file
    :type data: list, tuple
    """
    with open(filename, 'w') as file:
        json.dump(data, file, indent=4, sort_keys=True)


def write_xml(filename, element_tree):
    """ Write data to XML or GML file

    :param filename: name of XML or GML file to write data to
    :type filename: str
    :param element_tree: data as ElementTree object
    :type element_tree: xmlElementTree
    """
    return element_tree.write(filename)
    # this will write declaration tag in first line:
    # return element_tree.write(filename, encoding='utf-8', xml_declaration=True)


def write_numpy(filename, data):
    """ Write data as numpy file

    :param filename: name of numpy file to write data to
    :type filename: str
    :param data: data to write to numpy file
    :type data: numpy array
    """
    return np.save(filename, data)


def get_data_format(filename):
    """ Util function to guess format from filename extension

    :param filename: name of file
    :type filename: str
    :return: file extension
    :rtype: MimeType
    """
    fmt_ext = filename.split('.')[-1]
    return MimeType(MimeType.canonical_extension(fmt_ext))


def get_jp2_bit_depth(stream):
    """ Reads bit encoding depth of jpeg2000 file in binary stream format

    :param stream: binary stream format
    :type stream: Binary I/O (e.g. io.BytesIO, io.BufferedReader, ...)
    :return: bit depth
    :rtype: int
    """
    stream.seek(0)
    while True:
        read_buffer = stream.read(8)
        if len(read_buffer) < 8:
            raise ValueError('Image Header Box not found in Jpeg2000 file')

        _, box_id = struct.unpack('>I4s', read_buffer)

        if box_id == b'ihdr':
            read_buffer = stream.read(14)
            params = struct.unpack('>IIHBBBB', read_buffer)
            return (params[3] & 0x7f) + 1


def fix_jp2_image(image, bit_depth):
    """ Because Pillow library incorrectly reads JPEG 2000 images with 15-bit encoding this function corrects the
    values in image.

    :param image: image read by opencv library
    :type image: numpy array
    :param bit_depth: bit depth of jp2 image encoding
    :type bit_depth: int
    :return: corrected image
    :rtype: numpy array
    """
    if bit_depth in [8, 16]:
        return image
    if bit_depth == 15:
        try:
            return image >> 1
        except TypeError:
            raise IOError('Failed to read JPEG 2000 image correctly. Most likely reason is that Pillow did not '
                          'install OpenJPEG library correctly. Try reinstalling Pillow from a wheel')

    raise ValueError('Bit depth {} of jp2 image is currently not supported. '
                     'Please raise an issue on package Github page'.format(bit_depth))
