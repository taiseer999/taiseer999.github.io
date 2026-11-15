# -*- coding: utf-8 -*-
"""
disc_udf.py - ABUKARIM TOOLS (4.8.79)

Reads the file system of a Blu-ray disc image (.iso) that sits behind a
link, a few ranged reads at a time, and returns every file of the disc
(BDMV/, CERTIFICATE/) with the byte ranges of the image that hold it.
disc_stream.py then serves those files as a folder on 127.0.0.1, so Kodi's
own Blu-ray reader opens the disc (menus, chapters, languages) and only the
parts it plays are ever downloaded.

Written for AB Tools from the published formats:
  ECMA-167 3rd ed. (volume / file structure, descriptor tags, ICBs, ADs)
  OSTA UDF 2.50 (type 2 metadata partition, extended file entries)
Blu-ray discs are UDF 2.50: file entries and directories are in the
metadata partition (itself a file in the physical partition); file
contents are in the physical partition.
"""
import struct

SECTOR = 2048
READ_SIZE = 128 * 1024        # one ranged request of the link
CACHE_PIECES = 64             # pieces kept while the image is walked (8 MB)
KEEP = ('BDMV', 'CERTIFICATE')
LIMIT_FILES = 5000
LIMIT_DEPTH = 8
LIMIT_DIR_BYTES = 8 << 20
LIMIT_AD_CHAIN = 2048
INLINE_MAX = 64 * 1024        # small inline (embedded) files are kept as bytes

# descriptor tag identifiers (ECMA-167 3/7.2.1, 4/7.2.1)
TAG_AVDP, TAG_PD, TAG_LVD, TAG_TD = 2, 5, 6, 8
TAG_FSD, TAG_FID, TAG_AED, TAG_FE, TAG_EFE = 256, 257, 258, 261, 266


class UdfError(Exception):
    pass


def _le16(buf, at):
    return struct.unpack_from('<H', buf, at)[0]


def _le32(buf, at):
    return struct.unpack_from('<I', buf, at)[0]


def _le64(buf, at):
    return struct.unpack_from('<Q', buf, at)[0]


def tag_id(buf, *wanted):
    """The tag identifier of the descriptor at buf[0:16] when its checksum is
    right (and it is one of `wanted`, if given); None otherwise."""
    if len(buf) < 16:
        return None
    total = 0
    for i in range(16):
        if i != 4:
            total += buf[i]
    if total & 0xFF != buf[4]:
        return None
    ident = _le16(buf, 0)
    if wanted and ident not in wanted:
        return None
    return ident


def dstring(raw):
    """A file identifier (OSTA compressed unicode: 8 = 1 byte, 16 = UTF-16BE)."""
    if not raw:
        return ''
    kind, body = raw[0], bytes(raw[1:])
    if kind == 16:
        return body[:len(body) // 2 * 2].decode('utf-16-be', 'replace')
    return body.decode('latin-1')


class _Extent(object):
    __slots__ = ('length', 'kind', 'block', 'ref')

    def __init__(self, length, kind, block, ref):
        self.length, self.kind, self.block, self.ref = length, kind, block, ref


class Image(object):
    """read(offset, length) -> bytes fetches a range of the image."""

    def __init__(self, read, size):
        self._read = read
        self.size = int(size or 0)
        self.reads = 0
        self._pieces = {}
        self._order = []
        self.block = SECTOR
        self.parts = {}          # partition number -> start sector (physical)
        self.maps = []           # partition maps, by reference number

    # ── reading ──
    def read(self, offset, length):
        """Bytes [offset, offset+length) of the image, through a small cache."""
        out = []
        while length > 0:
            piece = offset // READ_SIZE
            data = self._piece(piece)
            at = offset - piece * READ_SIZE
            take = data[at:at + length]
            if not take:
                raise UdfError('read past the end of the image at %d' % offset)
            out.append(take)
            offset += len(take)
            length -= len(take)
        return b''.join(out)

    def _piece(self, piece):
        data = self._pieces.get(piece)
        if data is not None:
            return data
        start = piece * READ_SIZE
        want = READ_SIZE
        if self.size:
            want = max(0, min(READ_SIZE, self.size - start))
        if want <= 0:
            return b''
        data = self._read(start, want)
        self.reads += 1
        if not data:
            raise UdfError('no data at %d' % start)
        self._pieces[piece] = data
        self._order.append(piece)
        if len(self._order) > CACHE_PIECES:
            self._pieces.pop(self._order.pop(0), None)
        return data

    def sector(self, number, count=1):
        return self.read(number * SECTOR, count * SECTOR)

    # ── volume structure ──
    def open(self):
        avdp = self.sector(256)
        if tag_id(avdp, TAG_AVDP) is None:
            raise UdfError('no anchor at sector 256 (not a UDF disc image)')
        vds_len, vds_at = _le32(avdp, 16), _le32(avdp, 20)
        lvd = None
        for i in range(max(1, min(vds_len // SECTOR, 64))):
            d = self.sector(vds_at + i)
            ident = tag_id(d)
            if ident == TAG_PD:
                self.parts[_le16(d, 22)] = _le32(d, 188)
            elif ident == TAG_LVD:
                lvd = d
            elif ident == TAG_TD:
                break
        if lvd is None or not self.parts:
            raise UdfError('no logical volume / partition descriptor')
        self.block = _le32(lvd, 212) or SECTOR
        if self.block != SECTOR:
            raise UdfError('block size %d is not supported' % self.block)
        self._read_maps(lvd)
        fsd_ad = self._long_ad(lvd, 248)
        fsd = self.read(self._address(fsd_ad.ref, fsd_ad.block), SECTOR)
        if tag_id(fsd, TAG_FSD) is None:
            raise UdfError('no file set descriptor')
        self.root = self._long_ad(fsd, 400)
        return self

    def _read_maps(self, lvd):
        count, at = _le32(lvd, 268), 440
        end = 440 + _le32(lvd, 264)
        for _ in range(count):
            if at + 2 > end:
                break
            kind, length = lvd[at], lvd[at + 1]
            if kind == 1:
                self.maps.append({'kind': 'physical', 'part': _le16(lvd, at + 4)})
            elif kind == 2 and b'*UDF Metadata Partition' in bytes(lvd[at + 4:at + 36]):
                self.maps.append({'kind': 'metadata', 'part': _le16(lvd, at + 38),
                                  'file': _le32(lvd, at + 40), 'extents': None})
            else:
                self.maps.append({'kind': 'other', 'part': _le16(lvd, at + 4) if length >= 6 else 0})
            at += max(length, 2)
        if not self.maps:
            self.maps.append({'kind': 'physical', 'part': min(self.parts)})
        for m in self.maps:
            if m['kind'] == 'metadata':
                m['extents'] = self._metadata_extents(m)

    def _physical_ref(self, part):
        for i, m in enumerate(self.maps):
            if m['kind'] == 'physical' and m['part'] == part:
                return i
        for i, m in enumerate(self.maps):
            if m['kind'] == 'physical':
                return i
        raise UdfError('no physical partition map')

    def _metadata_extents(self, meta):
        """[(first metadata block, sector count, absolute sector), ...] of the metadata file."""
        start = self.parts.get(meta['part'])
        if start is None:
            raise UdfError('metadata partition points at a missing partition')
        entry = self.sector(start + meta['file'])
        if tag_id(entry, TAG_FE, TAG_EFE) is None:
            raise UdfError('no metadata file entry')
        out, block = [], 0
        for ext in self._entry_extents(entry, self._physical_ref(meta['part'])):
            if ext.kind != 0:
                continue
            count = (ext.length + SECTOR - 1) // SECTOR
            out.append((block, count, self.parts[meta['part']] + ext.block))
            block += count
        if not out:
            raise UdfError('empty metadata file')
        return out

    def _address(self, ref, block):
        """Byte offset in the image of logical block `block` of partition reference `ref`."""
        if ref >= len(self.maps):
            raise UdfError('partition reference %d out of range' % ref)
        m = self.maps[ref]
        if m['kind'] == 'metadata':
            for first, count, sector in m['extents']:
                if first <= block < first + count:
                    return (sector + block - first) * SECTOR
            raise UdfError('metadata block %d is not mapped' % block)
        start = self.parts.get(m['part'])
        if start is None:
            raise UdfError('partition %d is missing' % m['part'])
        return (start + block) * SECTOR

    def _data_ref(self, ref):
        """File contents: UDF 2.50 keeps them in the physical partition even when
        the short_ad sits in an entry of the metadata partition."""
        if ref < len(self.maps) and self.maps[ref]['kind'] == 'metadata':
            return self._physical_ref(self.maps[ref]['part'])
        return ref

    # ── file entries ──
    @staticmethod
    def _long_ad(buf, at):
        raw = _le32(buf, at)
        return _Extent(raw & 0x3FFFFFFF, raw >> 30, _le32(buf, at + 4), _le16(buf, at + 8))

    @staticmethod
    def _entry_layout(entry):
        """(info length, allocation type, ADs start, ADs length, file type)."""
        flags = _le16(entry, 16 + 18)
        ftype = entry[16 + 11]
        if _le16(entry, 0) == TAG_EFE:
            ea, ad = _le32(entry, 208), _le32(entry, 212)
            base = 216
        else:
            ea, ad = _le32(entry, 168), _le32(entry, 172)
            base = 176
        return _le64(entry, 56), flags & 7, base + ea, ad, ftype

    def _entry_extents(self, entry, ref):
        """Every data extent of a file entry (continuation extents followed)."""
        _size, kind, at, length, _ft = self._entry_layout(entry)
        if kind == 3:
            return []
        if kind not in (0, 1):
            raise UdfError('allocation descriptor type %d is not supported' % kind)
        out, chain = [], 0
        buf, end = entry, at + length
        while True:
            nxt = None
            step = 8 if kind == 0 else 16
            while at + step <= end:
                if kind == 0:
                    raw = _le32(buf, at)
                    ext = _Extent(raw & 0x3FFFFFFF, raw >> 30, _le32(buf, at + 4), ref)
                else:
                    ext = self._long_ad(buf, at)
                at += step
                if ext.length == 0:
                    break
                if ext.kind == 3:
                    nxt = ext
                    break
                out.append(ext)
            if nxt is None:
                return out
            chain += 1
            if chain > LIMIT_AD_CHAIN:
                raise UdfError('too many allocation extent descriptors')
            buf = self.read(self._address(nxt.ref, nxt.block), SECTOR)
            if tag_id(buf, TAG_AED) is None:
                raise UdfError('bad allocation extent descriptor')
            at, end = 24, 24 + _le32(buf, 20)

    def _entry(self, icb):
        entry = self.read(self._address(icb.ref, icb.block), SECTOR)
        if tag_id(entry, TAG_FE, TAG_EFE) is None:
            raise UdfError('no file entry at block %d' % icb.block)
        return entry

    def _directory(self, icb):
        """[(name, is_dir, icb), ...] of a directory."""
        entry = self._entry(icb)
        size, kind, at, length, _ft = self._entry_layout(entry)
        if size > LIMIT_DIR_BYTES:
            raise UdfError('directory too large')
        if kind == 3:
            data = bytes(entry[at:at + min(length, size)])
        else:
            parts = []
            for ext in self._entry_extents(entry, icb.ref):
                if ext.kind != 0:
                    continue
                parts.append(self.read(self._address(ext.ref, ext.block), ext.length))
            data = b''.join(parts)[:size]
        out, at = [], 0
        while at + 38 <= len(data):
            if tag_id(data[at:at + 16], TAG_FID) is None:
                break
            chars, name_len = data[at + 18], data[at + 19]
            child = self._long_ad(data, at + 20)
            iu_len = _le16(data, at + 36)
            name_at = at + 38 + iu_len
            if not chars & 0x08 and not chars & 0x04:           # not parent, not deleted
                out.append((dstring(data[name_at:name_at + name_len]), bool(chars & 0x02), child))
            at += (38 + iu_len + name_len + 3) & ~3
        return out

    def _file(self, icb):
        """{'size', 'x': [[offset, length], ...]} or {'size', 'data': hex} for inline files."""
        entry = self._entry(icb)
        size, kind, at, length, _ft = self._entry_layout(entry)
        if kind == 3:
            return {'size': size, 'data': bytes(entry[at:at + min(length, size, INLINE_MAX)]).hex()}
        ranges, left = [], size
        for ext in self._entry_extents(entry, icb.ref):
            if left <= 0:
                break
            take = min(ext.length, left)
            if ext.kind == 0:
                ranges.append([self._address(self._data_ref(ext.ref), ext.block), take])
            else:
                ranges.append([-1, take])                       # not recorded: zeros
            left -= take
        return {'size': size, 'x': ranges}

    def disc_files(self):
        """{'BDMV/index.bdmv': {...}, ...} for the folders a Blu-ray player needs."""
        files = {}

        def walk(icb, prefix, depth):
            if depth > LIMIT_DEPTH:
                return
            for name, is_dir, child in self._directory(icb):
                if not name:
                    continue
                if not prefix and name.upper() not in KEEP:
                    continue
                rel = prefix + name
                if is_dir:
                    files[rel + '/'] = {'dir': True}
                    walk(child, rel + '/', depth + 1)
                else:
                    files[rel] = self._file(child)
                if len(files) > LIMIT_FILES:
                    raise UdfError('too many files on the disc')

        walk(self.root, '', 0)
        if not any(k.upper() == 'BDMV/INDEX.BDMV' for k in files):
            raise UdfError('no BDMV/index.bdmv - not a Blu-ray image')
        return files


def file_bytes(image, entry, limit=1 << 20):
    """The first `limit` bytes of a file found by disc_files()."""
    if entry.get('data') is not None:
        return bytes.fromhex(entry['data'])[:limit]
    out, left = [], min(int(entry.get('size') or 0), limit)
    for offset, length in entry.get('x') or []:
        if left <= 0:
            break
        take = min(length, left)
        out.append(b'\0' * take if offset < 0 else image.read(offset, take))
        left -= take
    return b''.join(out)
