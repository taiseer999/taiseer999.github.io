# -*- coding: utf-8 -*-
"""
patcher.py  –  ABUKARIM TOOLS
Applies patches to installed Kodi addons.
"""

import base64
import os
import re
import time
import xbmc
import xbmcvfs
import xbmcgui



# ── Composite for Plex QR Auth blobs (by ABUKARIM TOOLS) ──
# ── TMDbHelper Trakt QR Auth blobs (by ABUKARIM TOOLS) ──
_TMDBH_QR_UTILS_B64 = 'IyAtKi0gY29kaW5nOiB1dGYtOCAtKi0KIiIiClFSIENvZGUgdXRpbGl0aWVzIGZvciBUTURiSGVscGVyIChUcmFrdCBkZXZpY2UgYXV0aCkK2YrZiNmE2ZHYryBRUiBQTkcg2YHZiiBhZGRvbl9kYXRhINmI2YrYsdis2Lkgc3BlY2lhbDovLyBwYXRoCkluamVjdGVkIGJ5IEFCVUtBUklNIFRPT0xTCiIiIgppbXBvcnQgb3MKaW1wb3J0IHN5cwppbXBvcnQgeGJtYwppbXBvcnQgeGJtY2FkZG9uCmltcG9ydCB4Ym1jdmZzCgoKZGVmIF9pbmplY3RfcXJfcGF0aHMoKToKICAgIHRyeToKICAgICAgICBvdXJfcGF0aCAgICA9IHhibWNhZGRvbi5BZGRvbigncGx1Z2luLnZpZGVvLnRoZW1vdmllZGIuaGVscGVyJykuZ2V0QWRkb25JbmZvKCdwYXRoJykKICAgICAgICBhZGRvbnNfcm9vdCA9IG9zLnBhdGguZGlybmFtZShvdXJfcGF0aCkKICAgICAgICBmb3IgbW9kdWxlIGluICgnc2NyaXB0Lm1vZHVsZS5xcmNvZGUnLCAnc2NyaXB0Lm1vZHVsZS5waWwnKToKICAgICAgICAgICAgbGliX3BhdGggPSBvcy5wYXRoLmpvaW4oYWRkb25zX3Jvb3QsIG1vZHVsZSwgJ2xpYicpCiAgICAgICAgICAgIGlmIG9zLnBhdGguaXNkaXIobGliX3BhdGgpIGFuZCBsaWJfcGF0aCBub3QgaW4gc3lzLnBhdGg6CiAgICAgICAgICAgICAgICBzeXMucGF0aC5pbnNlcnQoMCwgbGliX3BhdGgpCiAgICBleGNlcHQgRXhjZXB0aW9uOgogICAgICAgIHBhc3MKCgpkZWYgX2dldF9xcl9zcGVjaWFsX3BhdGgoKToKICAgICIiItmF2LPYp9ixINir2KfYqNiqINmB2YogYWRkb25fZGF0YSDZiti22YXZhiDZiNi12YjZhCBLb2RpINil2YTZitmHIiIiCiAgICByZXR1cm4gJ3NwZWNpYWw6Ly9wcm9maWxlL2FkZG9uX2RhdGEvcGx1Z2luLnZpZGVvLnRoZW1vdmllZGIuaGVscGVyL3RyYWt0X2F1dGhfcXIucG5nJwoKCmRlZiBfbWFrZV9xcl9sb2NhbCh1cmwsIG9zX3BhdGgpOgogICAgaW1wb3J0IHFyY29kZQogICAgaW1nID0gcXJjb2RlLm1ha2UodXJsKQogICAgaW1nLnNhdmUob3NfcGF0aCkKICAgIHJldHVybiBUcnVlCgoKZGVmIF9tYWtlX3FyX3JlbW90ZSh1cmwsIG9zX3BhdGgpOgogICAgZnJvbSB1cmxsaWIucmVxdWVzdCBpbXBvcnQgdXJsb3BlbgogICAgZnJvbSB1cmxsaWIucGFyc2UgICBpbXBvcnQgcXVvdGUKICAgIGFwaV91cmwgPSAnaHR0cHM6Ly9hcGkucXJzZXJ2ZXIuY29tL3YxL2NyZWF0ZS1xci1jb2RlLz9zaXplPTQwMHg0MDAmZGF0YT0nICsgcXVvdGUodXJsLCBzYWZlPScnKQogICAgd2l0aCB1cmxvcGVuKGFwaV91cmwsIHRpbWVvdXQ9MTApIGFzIHJlc3A6CiAgICAgICAgZGF0YSA9IHJlc3AucmVhZCgpCiAgICBpZiBsZW4oZGF0YSkgPCAxMDA6CiAgICAgICAgcmFpc2UgVmFsdWVFcnJvcignRW1wdHkgUVIgcmVzcG9uc2UnKQogICAgd2l0aCBvcGVuKG9zX3BhdGgsICd3YicpIGFzIGY6CiAgICAgICAgZi53cml0ZShkYXRhKQogICAgcmV0dXJuIFRydWUKCgpkZWYgbWFrZV9xcih1cmwpOgogICAgIiIiCiAgICDZitmI2YTZkdivIFFSIFBORyDZgdmKIGFkZG9uX2RhdGEg2YjZitix2KzYuSBzcGVjaWFsOi8vIHBhdGgKICAgIGFkZG9uX2RhdGEg2YXYttmF2YjZhiDYo9mGIEtvZGkg2YrYrdmF2ZHZhCDZhdmG2Ycg2KfZhNi12YjYsSDZhdio2KfYtNix2KkKICAgICIiIgogICAgX2luamVjdF9xcl9wYXRocygpCgogICAgc3BlY2lhbF9wYXRoID0gX2dldF9xcl9zcGVjaWFsX3BhdGgoKQogICAgb3NfcGF0aCAgICAgID0geGJtY3Zmcy50cmFuc2xhdGVQYXRoKHNwZWNpYWxfcGF0aCkKCiAgICBvcy5tYWtlZGlycyhvcy5wYXRoLmRpcm5hbWUob3NfcGF0aCksIGV4aXN0X29rPVRydWUpCgogICAgIyDZhdit2KfZiNmE2KkgMTog2YXYrdmE2YoKICAgIHRyeToKICAgICAgICBfbWFrZV9xcl9sb2NhbCh1cmwsIG9zX3BhdGgpCiAgICAgICAgeGJtYy5sb2coZidUTURiSGVscGVyIFFSIGxvY2FsIE9LOiB7c3BlY2lhbF9wYXRofScsIHhibWMuTE9HSU5GTykKICAgICAgICByZXR1cm4gc3BlY2lhbF9wYXRoCiAgICBleGNlcHQgRXhjZXB0aW9uIGFzIGU6CiAgICAgICAgeGJtYy5sb2coZidUTURiSGVscGVyIFFSIGxvY2FsIGZhaWxlZDoge2V9IOKAlCB0cnlpbmcgcmVtb3RlJywgeGJtYy5MT0dJTkZPKQoKICAgICMg2YXYrdin2YjZhNipIDI6IEFQSQogICAgdHJ5OgogICAgICAgIF9tYWtlX3FyX3JlbW90ZSh1cmwsIG9zX3BhdGgpCiAgICAgICAgeGJtYy5sb2coZidUTURiSGVscGVyIFFSIHJlbW90ZSBPSzoge3NwZWNpYWxfcGF0aH0nLCB4Ym1jLkxPR0lORk8pCiAgICAgICAgcmV0dXJuIHNwZWNpYWxfcGF0aAogICAgZXhjZXB0IEV4Y2VwdGlvbiBhcyBlOgogICAgICAgIHhibWMubG9nKGYnVE1EYkhlbHBlciBRUiByZW1vdGUgZmFpbGVkOiB7ZX0nLCB4Ym1jLkxPR1dBUk5JTkcpCgogICAgcmV0dXJuICcnCgoKZGVmIHJlbW92ZV9xcihwYXRoKToKICAgIHRyeToKICAgICAgICBpZiBwYXRoOgogICAgICAgICAgICBvc19wYXRoID0geGJtY3Zmcy50cmFuc2xhdGVQYXRoKHBhdGgpIGlmIHBhdGguc3RhcnRzd2l0aCgnc3BlY2lhbDovLycpIGVsc2UgcGF0aAogICAgICAgICAgICBpZiBvcy5wYXRoLmV4aXN0cyhvc19wYXRoKToKICAgICAgICAgICAgICAgIG9zLnJlbW92ZShvc19wYXRoKQogICAgZXhjZXB0IEV4Y2VwdGlvbjoKICAgICAgICBwYXNzCgoKIyAtLSBUcmFrdCBRUiBkaWFsb2cgd2luZG93IChCYWNrIHRvIGNhbmNlbCkgLSBBQlVLQVJJTSBUT09MUyAtLQpkZWYgZ2V0X3FyX2RpYWxvZyhhZGRvbl9wYXRoKToKICAgICIiIlJldHVybnMgYW4gaW5zdGFuY2Ugb2YgYSBXaW5kb3dYTUxEaWFsb2cgc3ViY2xhc3MgdGhhdCB0cmFja3MgY2FuY2VsLiIiIgogICAgaW1wb3J0IHhibWNndWkKCiAgICBjbGFzcyBfVHJha3RRUkRpYWxvZyh4Ym1jZ3VpLldpbmRvd1hNTERpYWxvZyk6CiAgICAgICAgZGVmIF9faW5pdF9fKHNlbGYsICphcmdzLCAqKmt3YXJncyk6CiAgICAgICAgICAgIHN1cGVyKCkuX19pbml0X18oKQogICAgICAgICAgICBzZWxmLmlzX2NhbmNlbGVkID0gRmFsc2UKCiAgICAgICAgZGVmIG9uQWN0aW9uKHNlbGYsIGFjdGlvbik6CiAgICAgICAgICAgICMgMTAgPSBQUkVWSU9VU19NRU5VIChFU0MpLCA5MiA9IE5BVl9CQUNLLCAxMTAgPSBCQUNLU1BBQ0UKICAgICAgICAgICAgaWYgYWN0aW9uLmdldElkKCkgaW4gKDEwLCA5MiwgMTEwKToKICAgICAgICAgICAgICAgIHNlbGYuaXNfY2FuY2VsZWQgPSBUcnVlCiAgICAgICAgICAgICAgICBzZWxmLmNsb3NlKCkKCiAgICByZXR1cm4gX1RyYWt0UVJEaWFsb2coJ3RyYWt0X2F1dGhfcXIueG1sJywgYWRkb25fcGF0aCwgJ0RlZmF1bHQnLCAnMTA4MGknKQo='
_TMDBH_TRAKT_XML_B64 = 'PHdpbmRvdyB0eXBlPSJkaWFsb2ciPgogICAgPGNvb3JkaW5hdGVzPgogICAgICAgIDxsZWZ0PjA8L2xlZnQ+CiAgICAgICAgPHRvcD4wPC90b3A+CiAgICAgICAgPHdpZHRoPjE5MjA8L3dpZHRoPgogICAgICAgIDxoZWlnaHQ+MTA4MDwvaGVpZ2h0PgogICAgPC9jb29yZGluYXRlcz4KICAgIDxjb250cm9scz4KCiAgICAgICAgPCEtLSBEaW0gb3ZlcmxheSAtLT4KICAgICAgICA8Y29udHJvbCB0eXBlPSJpbWFnZSI+CiAgICAgICAgICAgIDxsZWZ0PjA8L2xlZnQ+PHRvcD4wPC90b3A+CiAgICAgICAgICAgIDx3aWR0aD4xOTIwPC93aWR0aD48aGVpZ2h0PjEwODA8L2hlaWdodD4KICAgICAgICAgICAgPHRleHR1cmUgYmFja2dyb3VuZD0idHJ1ZSI+d2hpdGUucG5nPC90ZXh0dXJlPgogICAgICAgICAgICA8Y29sb3JkaWZmdXNlPkQwMDAwMDAwPC9jb2xvcmRpZmZ1c2U+CiAgICAgICAgPC9jb250cm9sPgoKICAgICAgICA8IS0tIENhcmQgYmFja2dyb3VuZCAtLT4KICAgICAgICA8Y29udHJvbCB0eXBlPSJpbWFnZSI+CiAgICAgICAgICAgIDxsZWZ0PjQxMDwvbGVmdD48dG9wPjE2NTwvdG9wPgogICAgICAgICAgICA8d2lkdGg+MTEwMDwvd2lkdGg+PGhlaWdodD43NTA8L2hlaWdodD4KICAgICAgICAgICAgPHRleHR1cmUgYmFja2dyb3VuZD0idHJ1ZSI+d2hpdGUucG5nPC90ZXh0dXJlPgogICAgICAgICAgICA8Y29sb3JkaWZmdXNlPkZGMUExQTFBPC9jb2xvcmRpZmZ1c2U+CiAgICAgICAgPC9jb250cm9sPgoKICAgICAgICA8IS0tIEdyZWVuIHRvcCBiYXIgLS0+CiAgICAgICAgPGNvbnRyb2wgdHlwZT0iaW1hZ2UiPgogICAgICAgICAgICA8bGVmdD40MTA8L2xlZnQ+PHRvcD4xNjU8L3RvcD4KICAgICAgICAgICAgPHdpZHRoPjExMDA8L3dpZHRoPjxoZWlnaHQ+ODwvaGVpZ2h0PgogICAgICAgICAgICA8dGV4dHVyZSBiYWNrZ3JvdW5kPSJ0cnVlIj53aGl0ZS5wbmc8L3RleHR1cmU+CiAgICAgICAgICAgIDxjb2xvcmRpZmZ1c2U+RkYwMEI5NjQ8L2NvbG9yZGlmZnVzZT4KICAgICAgICA8L2NvbnRyb2w+CgogICAgICAgIDwhLS0gVGl0bGUgLS0+CiAgICAgICAgPGNvbnRyb2wgdHlwZT0ibGFiZWwiPgogICAgICAgICAgICA8bGVmdD40MTA8L2xlZnQ+PHRvcD4xOTU8L3RvcD4KICAgICAgICAgICAgPHdpZHRoPjExMDA8L3dpZHRoPjxoZWlnaHQ+NjA8L2hlaWdodD4KICAgICAgICAgICAgPGFsaWduPmNlbnRlcjwvYWxpZ24+CiAgICAgICAgICAgIDxmb250PmZvbnQyNzwvZm9udD4KICAgICAgICAgICAgPHRleHRjb2xvcj5GRjAwQjk2NDwvdGV4dGNvbG9yPgogICAgICAgICAgICA8bGFiZWw+VHJha3QgQXV0aGVudGljYXRpb248L2xhYmVsPgogICAgICAgIDwvY29udHJvbD4KCiAgICAgICAgPCEtLSBRUiB3aGl0ZSBiYWNrZ3JvdW5kIC0tPgogICAgICAgIDxjb250cm9sIHR5cGU9ImltYWdlIj4KICAgICAgICAgICAgPGxlZnQ+NDU1PC9sZWZ0Pjx0b3A+Mjc1PC90b3A+CiAgICAgICAgICAgIDx3aWR0aD40MjA8L3dpZHRoPjxoZWlnaHQ+NDIwPC9oZWlnaHQ+CiAgICAgICAgICAgIDx0ZXh0dXJlIGJhY2tncm91bmQ9InRydWUiPndoaXRlLnBuZzwvdGV4dHVyZT4KICAgICAgICAgICAgPGNvbG9yZGlmZnVzZT5GRkZGRkZGRjwvY29sb3JkaWZmdXNlPgogICAgICAgIDwvY29udHJvbD4KCiAgICAgICAgPCEtLSBRUiBDb2RlIC0tPgogICAgICAgIDxjb250cm9sIHR5cGU9ImltYWdlIj4KICAgICAgICAgICAgPGxlZnQ+NDY1PC9sZWZ0Pjx0b3A+Mjg1PC90b3A+CiAgICAgICAgICAgIDx3aWR0aD40MDA8L3dpZHRoPjxoZWlnaHQ+NDAwPC9oZWlnaHQ+CiAgICAgICAgICAgIDxhc3BlY3RyYXRpbz5zdHJldGNoPC9hc3BlY3RyYXRpbz4KICAgICAgICAgICAgPHRleHR1cmU+JElORk9bV2luZG93KCkuUHJvcGVydHkocXJfaW1hZ2UpXTwvdGV4dHVyZT4KICAgICAgICA8L2NvbnRyb2w+CgogICAgICAgIDwhLS0gU2NhbiBpbnN0cnVjdGlvbiAtLT4KICAgICAgICA8Y29udHJvbCB0eXBlPSJsYWJlbCI+CiAgICAgICAgICAgIDxsZWZ0PjkzMDwvbGVmdD48dG9wPjI5NTwvdG9wPgogICAgICAgICAgICA8d2lkdGg+NTMwPC93aWR0aD48aGVpZ2h0PjQwPC9oZWlnaHQ+CiAgICAgICAgICAgIDxmb250PmZvbnQxMjwvZm9udD4KICAgICAgICAgICAgPHRleHRjb2xvcj5GRkFBQUFBQTwvdGV4dGNvbG9yPgogICAgICAgICAgICA8bGFiZWw+U2NhbiBRUiBjb2RlIG9yIHZpc2l0OjwvbGFiZWw+CiAgICAgICAgPC9jb250cm9sPgoKICAgICAgICA8IS0tIFVSTCAtLT4KICAgICAgICA8Y29udHJvbCB0eXBlPSJsYWJlbCI+CiAgICAgICAgICAgIDxsZWZ0PjkzMDwvbGVmdD48dG9wPjM1MDwvdG9wPgogICAgICAgICAgICA8d2lkdGg+NTMwPC93aWR0aD48aGVpZ2h0PjQwPC9oZWlnaHQ+CiAgICAgICAgICAgIDxmb250PmZvbnQxMjwvZm9udD4KICAgICAgICAgICAgPHRleHRjb2xvcj5GRjAwQjk2NDwvdGV4dGNvbG9yPgogICAgICAgICAgICA8bGFiZWw+aHR0cHM6Ly90cmFrdC50di9hY3RpdmF0ZTwvbGFiZWw+CiAgICAgICAgPC9jb250cm9sPgoKICAgICAgICA8IS0tIERpdmlkZXIgLS0+CiAgICAgICAgPGNvbnRyb2wgdHlwZT0iaW1hZ2UiPgogICAgICAgICAgICA8bGVmdD45MzA8L2xlZnQ+PHRvcD40MTA8L3RvcD4KICAgICAgICAgICAgPHdpZHRoPjUzMDwvd2lkdGg+PGhlaWdodD4yPC9oZWlnaHQ+CiAgICAgICAgICAgIDx0ZXh0dXJlIGJhY2tncm91bmQ9InRydWUiPndoaXRlLnBuZzwvdGV4dHVyZT4KICAgICAgICAgICAgPGNvbG9yZGlmZnVzZT40NEZGRkZGRjwvY29sb3JkaWZmdXNlPgogICAgICAgIDwvY29udHJvbD4KCiAgICAgICAgPCEtLSBFbnRlciBDb2RlIGxhYmVsIC0tPgogICAgICAgIDxjb250cm9sIHR5cGU9ImxhYmVsIj4KICAgICAgICAgICAgPGxlZnQ+OTMwPC9sZWZ0Pjx0b3A+NDMwPC90b3A+CiAgICAgICAgICAgIDx3aWR0aD41MzA8L3dpZHRoPjxoZWlnaHQ+NDA8L2hlaWdodD4KICAgICAgICAgICAgPGZvbnQ+Zm9udDEyPC9mb250PgogICAgICAgICAgICA8dGV4dGNvbG9yPkZGQUFBQUFBPC90ZXh0Y29sb3I+CiAgICAgICAgICAgIDxsYWJlbD5FbnRlciB0aGlzIGNvZGU6PC9sYWJlbD4KICAgICAgICA8L2NvbnRyb2w+CgogICAgICAgIDwhLS0gQ29kZSBib3ggYm9yZGVyIC0tPgogICAgICAgIDxjb250cm9sIHR5cGU9ImltYWdlIj4KICAgICAgICAgICAgPGxlZnQ+OTMwPC9sZWZ0Pjx0b3A+NDgwPC90b3A+CiAgICAgICAgICAgIDx3aWR0aD41MzA8L3dpZHRoPjxoZWlnaHQ+ODA8L2hlaWdodD4KICAgICAgICAgICAgPHRleHR1cmUgYmFja2dyb3VuZD0idHJ1ZSI+d2hpdGUucG5nPC90ZXh0dXJlPgogICAgICAgICAgICA8Y29sb3JkaWZmdXNlPkZGMDBCOTY0PC9jb2xvcmRpZmZ1c2U+CiAgICAgICAgPC9jb250cm9sPgoKICAgICAgICA8IS0tIENvZGUgYm94IGZpbGwgLS0+CiAgICAgICAgPGNvbnRyb2wgdHlwZT0iaW1hZ2UiPgogICAgICAgICAgICA8bGVmdD45MzQ8L2xlZnQ+PHRvcD40ODQ8L3RvcD4KICAgICAgICAgICAgPHdpZHRoPjUyMjwvd2lkdGg+PGhlaWdodD43MjwvaGVpZ2h0PgogICAgICAgICAgICA8dGV4dHVyZSBiYWNrZ3JvdW5kPSJ0cnVlIj53aGl0ZS5wbmc8L3RleHR1cmU+CiAgICAgICAgICAgIDxjb2xvcmRpZmZ1c2U+RkYxQTFBMUE8L2NvbG9yZGlmZnVzZT4KICAgICAgICA8L2NvbnRyb2w+CgogICAgICAgIDwhLS0gVXNlciBDb2RlIC0tPgogICAgICAgIDxjb250cm9sIHR5cGU9ImxhYmVsIj4KICAgICAgICAgICAgPGxlZnQ+OTMwPC9sZWZ0Pjx0b3A+NDg0PC90b3A+CiAgICAgICAgICAgIDx3aWR0aD41MzA8L3dpZHRoPjxoZWlnaHQ+NzI8L2hlaWdodD4KICAgICAgICAgICAgPGFsaWduPmNlbnRlcjwvYWxpZ24+CiAgICAgICAgICAgIDxhbGlnbnk+Y2VudGVyPC9hbGlnbnk+CiAgICAgICAgICAgIDxmb250PmZvbnQzNzwvZm9udD4KICAgICAgICAgICAgPHRleHRjb2xvcj5GRjAwQjk2NDwvdGV4dGNvbG9yPgogICAgICAgICAgICA8bGFiZWw+JElORk9bV2luZG93KCkuUHJvcGVydHkodXNlcl9jb2RlKV08L2xhYmVsPgogICAgICAgIDwvY29udHJvbD4KCiAgICAgICAgPCEtLSBQcm9ncmVzcyBiYXIgYmFja2dyb3VuZCAtLT4KICAgICAgICA8Y29udHJvbCB0eXBlPSJpbWFnZSI+CiAgICAgICAgICAgIDxsZWZ0PjkzMDwvbGVmdD48dG9wPjU5MDwvdG9wPgogICAgICAgICAgICA8d2lkdGg+NTMwPC93aWR0aD48aGVpZ2h0Pjg8L2hlaWdodD4KICAgICAgICAgICAgPHRleHR1cmUgYmFja2dyb3VuZD0idHJ1ZSI+d2hpdGUucG5nPC90ZXh0dXJlPgogICAgICAgICAgICA8Y29sb3JkaWZmdXNlPjQ0RkZGRkZGPC9jb2xvcmRpZmZ1c2U+CiAgICAgICAgPC9jb250cm9sPgoKICAgICAgICA8IS0tIFByb2dyZXNzIGJhciBmaWxsIC0tPgogICAgICAgIDxjb250cm9sIHR5cGU9ImltYWdlIj4KICAgICAgICAgICAgPGxlZnQ+OTMwPC9sZWZ0Pjx0b3A+NTkwPC90b3A+CiAgICAgICAgICAgIDx3aWR0aD4kSU5GT1tXaW5kb3coKS5Qcm9wZXJ0eShwcm9ncmVzc193aWR0aCldPC93aWR0aD48aGVpZ2h0Pjg8L2hlaWdodD4KICAgICAgICAgICAgPHRleHR1cmUgYmFja2dyb3VuZD0idHJ1ZSI+d2hpdGUucG5nPC90ZXh0dXJlPgogICAgICAgICAgICA8Y29sb3JkaWZmdXNlPkZGMDBCOTY0PC9jb2xvcmRpZmZ1c2U+CiAgICAgICAgPC9jb250cm9sPgoKICAgICAgICA8IS0tIEV4cGlyZXMgbGFiZWwgLS0+CiAgICAgICAgPGNvbnRyb2wgdHlwZT0ibGFiZWwiPgogICAgICAgICAgICA8bGVmdD45MzA8L2xlZnQ+PHRvcD42MTA8L3RvcD4KICAgICAgICAgICAgPHdpZHRoPjUzMDwvd2lkdGg+PGhlaWdodD4zNTwvaGVpZ2h0PgogICAgICAgICAgICA8Zm9udD5mb250X3Rpbnk8L2ZvbnQ+CiAgICAgICAgICAgIDx0ZXh0Y29sb3I+RkY4ODg4ODg8L3RleHRjb2xvcj4KICAgICAgICAgICAgPGxhYmVsPiRJTkZPW1dpbmRvdygpLlByb3BlcnR5KGV4cGlyZXNfbGFiZWwpXTwvbGFiZWw+CiAgICAgICAgPC9jb250cm9sPgoKICAgICAgICA8IS0tIENhbmNlbCBoaW50IC0tPgogICAgICAgIDxjb250cm9sIHR5cGU9ImxhYmVsIj4KICAgICAgICAgICAgPGxlZnQ+NDEwPC9sZWZ0Pjx0b3A+ODcwPC90b3A+CiAgICAgICAgICAgIDx3aWR0aD4xMTAwPC93aWR0aD48aGVpZ2h0PjM1PC9oZWlnaHQ+CiAgICAgICAgICAgIDxhbGlnbj5jZW50ZXI8L2FsaWduPgogICAgICAgICAgICA8Zm9udD5mb250X3Rpbnk8L2ZvbnQ+CiAgICAgICAgICAgIDx0ZXh0Y29sb3I+RkY2NjY2NjY8L3RleHRjb2xvcj4KICAgICAgICAgICAgPGxhYmVsPlByZXNzIEJhY2sgdG8gY2FuY2VsPC9sYWJlbD4KICAgICAgICA8L2NvbnRyb2w+CgogICAgPC9jb250cm9scz4KPC93aW5kb3c+Cg=='
_TMDBH_POLLER_OLD_B64 = 'ICAgIGRlZiBwb2xsZXIoc2VsZik6CgogICAgICAgIHdoaWxlIFRydWU6CgogICAgICAgICAgICBpZiBzZWxmLnhibWNfbW9uaXRvci5hYm9ydFJlcXVlc3RlZCgpOgogICAgICAgICAgICAgICAgc2VsZi5zdGF0ZSA9ICdhYm9ydGVkJwogICAgICAgICAgICAgICAgYnJlYWsKCiAgICAgICAgICAgIGlmIHNlbGYuYXV0aF9kaWFsb2cuaXNjYW5jZWxlZCgpOgogICAgICAgICAgICAgICAgc2VsZi5zdGF0ZSA9ICdhYm9ydGVkJwogICAgICAgICAgICAgICAgYnJlYWsKCiAgICAgICAgICAgIHNlbGYuYXV0aF9kaWFsb2dfdXBkYXRlKCkKCiAgICAgICAgICAgIGlmIHNlbGYuZXhwaXJlc19pbiA8PSBzZWxmLnByb2dyZXNzOgogICAgICAgICAgICAgICAgc2VsZi5zdGF0ZSA9ICdleHBpcmVkJwogICAgICAgICAgICAgICAgYnJlYWsKCiAgICAgICAgICAgIHNlbGYuYXV0aG9yaXphdGlvbiA9IHNlbGYudHJha3RfYXBpLmdldF9hdXRob3Jpc2F0aW9uX3Rva2VuKHNlbGYuZGV2aWNlX2NvZGUpCgogICAgICAgICAgICBpZiBzZWxmLmF1dGhvcml6YXRpb246CiAgICAgICAgICAgICAgICBzZWxmLnN0YXRlID0gJ3N1Y2Nlc3MnCiAgICAgICAgICAgICAgICBicmVhawoKICAgICAgICAgICAgc2VsZi54Ym1jX21vbml0b3Iud2FpdEZvckFib3J0KHNlbGYuaW50ZXJ2YWwpCgogICAgICAgIHNlbGYuYXV0aF9kaWFsb2dfY2xvc2UoKQo='
_TMDBH_POLLER_NEW_B64 = 'ICAgIGRlZiBwb2xsZXIoc2VsZik6CgogICAgICAgICMgLS0gVE1EYkhlbHBlciBUcmFrdCBRUiBBdXRoIHBhdGNoIChieSBBQlVLQVJJTSBUT09MUykgLS0KICAgICAgICBpbXBvcnQgeGJtY2FkZG9uIGFzIF94Ym1jYWRkb24KICAgICAgICBmcm9tIHRtZGJoZWxwZXIubGliLmFwaS50cmFrdC5xcl91dGlscyBpbXBvcnQgbWFrZV9xciwgcmVtb3ZlX3FyLCBnZXRfcXJfZGlhbG9nCgogICAgICAgIHFyX3VybCAgPSAnaHR0cHM6Ly90cmFrdC50di9hY3RpdmF0ZS8nICsgc3RyKHNlbGYudXNlcl9jb2RlKQogICAgICAgIHFyX3BhdGggPSBtYWtlX3FyKHFyX3VybCkKICAgICAgICBhZGRvbl9wYXRoID0gX3hibWNhZGRvbi5BZGRvbigncGx1Z2luLnZpZGVvLnRoZW1vdmllZGIuaGVscGVyJykuZ2V0QWRkb25JbmZvKCdwYXRoJykKCiAgICAgICAgcXJfZGlhbG9nID0gZ2V0X3FyX2RpYWxvZyhhZGRvbl9wYXRoKQogICAgICAgIHFyX2RpYWxvZy5zaG93KCkKICAgICAgICBxcl9kaWFsb2cuc2V0UHJvcGVydHkoJ3VzZXJfY29kZScsICAgICAgc3RyKHNlbGYudXNlcl9jb2RlKSkKICAgICAgICBxcl9kaWFsb2cuc2V0UHJvcGVydHkoJ3FyX2ltYWdlJywgICAgICAgcXJfcGF0aCkKICAgICAgICBxcl9kaWFsb2cuc2V0UHJvcGVydHkoJ3Byb2dyZXNzX3dpZHRoJywgJzUzMCcpCiAgICAgICAgcXJfZGlhbG9nLnNldFByb3BlcnR5KCdleHBpcmVzX2xhYmVsJywgICdFeHBpcmVzIGluICVzcycgJSBpbnQoc2VsZi5leHBpcmVzX2luKSkKCiAgICAgICAgdHJ5OgogICAgICAgICAgICB3aGlsZSBUcnVlOgoKICAgICAgICAgICAgICAgIGlmIHNlbGYueGJtY19tb25pdG9yLmFib3J0UmVxdWVzdGVkKCk6CiAgICAgICAgICAgICAgICAgICAgc2VsZi5zdGF0ZSA9ICdhYm9ydGVkJwogICAgICAgICAgICAgICAgICAgIGJyZWFrCgogICAgICAgICAgICAgICAgaWYgZ2V0YXR0cihxcl9kaWFsb2csICdpc19jYW5jZWxlZCcsIEZhbHNlKToKICAgICAgICAgICAgICAgICAgICBzZWxmLnN0YXRlID0gJ2Fib3J0ZWQnCiAgICAgICAgICAgICAgICAgICAgYnJlYWsKCiAgICAgICAgICAgICAgICBzZWxmLnByb2dyZXNzICs9IHNlbGYuaW50ZXJ2YWwKICAgICAgICAgICAgICAgIF9yZW1haW5pbmcgPSBtYXgoaW50KHNlbGYuZXhwaXJlc19pbikgLSBzZWxmLnByb2dyZXNzLCAwKQogICAgICAgICAgICAgICAgX3dpZHRoID0gaW50KGZsb2F0KF9yZW1haW5pbmcgKiA1MzApIC8gc2VsZi5leHBpcmVzX2luKSBpZiBzZWxmLmV4cGlyZXNfaW4gZWxzZSAwCiAgICAgICAgICAgICAgICBxcl9kaWFsb2cuc2V0UHJvcGVydHkoJ3Byb2dyZXNzX3dpZHRoJywgc3RyKF93aWR0aCkpCiAgICAgICAgICAgICAgICBxcl9kaWFsb2cuc2V0UHJvcGVydHkoJ2V4cGlyZXNfbGFiZWwnLCAgJ0V4cGlyZXMgaW4gJXNzJyAlIF9yZW1haW5pbmcpCgogICAgICAgICAgICAgICAgaWYgc2VsZi5leHBpcmVzX2luIDw9IHNlbGYucHJvZ3Jlc3M6CiAgICAgICAgICAgICAgICAgICAgc2VsZi5zdGF0ZSA9ICdleHBpcmVkJwogICAgICAgICAgICAgICAgICAgIGJyZWFrCgogICAgICAgICAgICAgICAgc2VsZi5hdXRob3JpemF0aW9uID0gc2VsZi50cmFrdF9hcGkuZ2V0X2F1dGhvcmlzYXRpb25fdG9rZW4oc2VsZi5kZXZpY2VfY29kZSkKCiAgICAgICAgICAgICAgICBpZiBzZWxmLmF1dGhvcml6YXRpb246CiAgICAgICAgICAgICAgICAgICAgc2VsZi5zdGF0ZSA9ICdzdWNjZXNzJwogICAgICAgICAgICAgICAgICAgIGJyZWFrCgogICAgICAgICAgICAgICAgc2VsZi54Ym1jX21vbml0b3Iud2FpdEZvckFib3J0KHNlbGYuaW50ZXJ2YWwpCiAgICAgICAgZmluYWxseToKICAgICAgICAgICAgdHJ5OgogICAgICAgICAgICAgICAgcXJfZGlhbG9nLmNsb3NlKCkKICAgICAgICAgICAgZXhjZXB0IEV4Y2VwdGlvbjoKICAgICAgICAgICAgICAgIHBhc3MKICAgICAgICAgICAgZGVsIHFyX2RpYWxvZwogICAgICAgICAgICByZW1vdmVfcXIocXJfcGF0aCkKCiAgICAgICAgc2VsZi5hdXRoX2RpYWxvZ19yb3V0ZSgpCiAgICAgICAgIyAtLSBlbmQgVE1EYkhlbHBlciBUcmFrdCBRUiBBdXRoIHBhdGNoIC0tCg=='


# TMDbHelper info.py - the Certification row is selected with iso_country=? where
# iso_country is the last 2 chars of the TMDbHelper language setting. With ar-SA that
# is 'SA', and TMDb carries almost no Saudi certifications, so mpaa came back empty for
# nearly every movie and show. TMDbHelper already caches EVERY country's certification
# in the same table, so the US value is present locally - only the WHERE clause hid it.
_TMDBH_CERTFALLBACK_OLD_B64 = 'Y2xhc3MgQ2VydGlmaWNhdGlvbihJdGVtRGV0YWlsc0xpc3QpOgogICAgdGFibGUgPSAnY2VydGlmaWNhdGlvbicKICAgIGtleXMgPSB0dXBsZShDRVJUSUZJQ0FUSU9OX0NPTFVNTlMua2V5cygpKQogICAgY29uZGl0aW9ucyA9ICdwYXJlbnRfaWQ9PyBBTkQgaXNvX2NvdW50cnk9PyBBTkQgbmFtZSBJUyBOT1QgTlVMTCBBTkQgbmFtZSAhPSAiIiBPUkRFUiBCWSBJRk5VTEwocmVsZWFzZV9kYXRlLCAiOTk5OS05OS05OSIpIEFTQyBMSU1JVCAxJyAgIyBXSEVSRSBjb25kaXRpb25zCiAgICBjb25mbGljdF9jb25zdHJhaW50ID0gJ2lzb19jb3VudHJ5LCBpc29fbGFuZ3VhZ2UsIHJlbGVhc2VfZGF0ZSwgcmVsZWFzZV90eXBlLCBwYXJlbnRfaWQnCgogICAgQHByb3BlcnR5CiAgICBkZWYgdmFsdWVzKHNlbGYpOiAgIyBXSEVSRSBjb25kaXRpb25zIHZhbHVlcyBmb3IgPwogICAgICAgIHJldHVybiAoc2VsZi5wYXJlbnRfaWQsIHNlbGYuY29tbW9uX2FwaXMudG1kYl9hcGkuaXNvX2NvdW50cnkpCg=='
_TMDBH_CERTFALLBACK_NEW_B64 = 'Y2xhc3MgQ2VydGlmaWNhdGlvbihJdGVtRGV0YWlsc0xpc3QpOgogICAgIyAtLSBVU0EgY2VydGlmaWNhdGlvbiBmYWxsYmFjayAoYnkgQUJVS0FSSU0gVE9PTFMpIC0tCiAgICB0YWJsZSA9ICdjZXJ0aWZpY2F0aW9uJwogICAga2V5cyA9IHR1cGxlKENFUlRJRklDQVRJT05fQ09MVU1OUy5rZXlzKCkpCiAgICBjb25kaXRpb25zID0gJ3BhcmVudF9pZD0/IEFORCBpc29fY291bnRyeSBJTiAoPywgIlVTIikgQU5EIG5hbWUgSVMgTk9UIE5VTEwgQU5EIG5hbWUgIT0gIiIgT1JERVIgQlkgaXNvX2NvdW50cnk9PyBERVNDLCBJRk5VTEwocmVsZWFzZV9kYXRlLCAiOTk5OS05OS05OSIpIEFTQyBMSU1JVCAxJyAgIyBXSEVSRSBjb25kaXRpb25zCiAgICBjb25mbGljdF9jb25zdHJhaW50ID0gJ2lzb19jb3VudHJ5LCBpc29fbGFuZ3VhZ2UsIHJlbGVhc2VfZGF0ZSwgcmVsZWFzZV90eXBlLCBwYXJlbnRfaWQnCgogICAgQHByb3BlcnR5CiAgICBkZWYgdmFsdWVzKHNlbGYpOiAgIyBXSEVSRSBjb25kaXRpb25zIHZhbHVlcyBmb3IgPwogICAgICAgIGlzb19jb3VudHJ5ID0gc2VsZi5jb21tb25fYXBpcy50bWRiX2FwaS5pc29fY291bnRyeQogICAgICAgIHJldHVybiAoc2VsZi5wYXJlbnRfaWQsIGlzb19jb3VudHJ5LCBpc29fY291bnRyeSkK'


# TMDbHelper ItemDetailsDatabase - genre language refresh (see the PATCHES entry).
_TMDBH_GENRE_LANG_BLOCK_V1 = (
    "\n"
    "    # -- TMDbHelper genre language refresh (by ABUKARIM TOOLS) --\n"
    "    # Genre rows carry no language and are never overwritten, so after a\n"
    "    # language change they stay in the old language. Clear them once and\n"
    "    # expire their items so they are refetched in the current language.\n"
    "    def create_database(self):\n"
    "        connection = super().create_database()\n"
    "        try:\n"
    "            self._abk_genre_language_refresh()\n"
    "        except Exception as error:\n"
    "            self.kodi_log(f'CACHE: ABK genre language refresh failed: {error}', 1)\n"
    "        return connection\n"
    "\n"
    "    def _abk_genre_language_refresh(self):\n"
    "        import sqlite3\n"
    "        from tmdbhelper.lib.addon.plugin import get_language\n"
    "        language = get_language() or 'en-US'\n"
    "        con = sqlite3.connect(self._db_file, timeout=self._db_timeout)\n"
    "        try:\n"
    "            with con:\n"
    "                con.execute('CREATE TABLE IF NOT EXISTS abk_meta(key TEXT PRIMARY KEY, value TEXT)')\n"
    "                row = con.execute(\"SELECT value FROM abk_meta WHERE key='genre_language'\").fetchone()\n"
    "                if row and row[0] == language:\n"
    "                    return\n"
    "                con.execute('UPDATE baseitem SET expiry=0 WHERE id IN (SELECT parent_id FROM genre)')\n"
    "                cleared = con.execute('DELETE FROM genre').rowcount\n"
    "                con.execute(\"INSERT OR REPLACE INTO abk_meta(key, value) VALUES ('genre_language', ?)\", (language, ))\n"
    "        finally:\n"
    "            con.close()\n"
    "        self.kodi_log(f'CACHE: ABK genre language refresh -> {language} ({cleared} genre rows cleared)', 1)\n"
)


# v2 (3.4.5): new sentinel + stamp key 'genre_language_v2' so boxes that ran v1
# while the global genre list (ItemQueries.db) was still English flush once more.
_TMDBH_GENRE_LANG_BLOCK = (
    _TMDBH_GENRE_LANG_BLOCK_V1
    .replace('# -- TMDbHelper genre language refresh (by ABUKARIM TOOLS) --',
             '# -- TMDbHelper genre language refresh v2 (by ABUKARIM TOOLS) --')
    .replace("key='genre_language'", "key='genre_language_v2'")
    .replace("VALUES ('genre_language', ?)", "VALUES ('genre_language_v2', ?)")
)

# TMDbHelper FindQueriesDatabase (ItemQueries.db) - the global genre list that
# every item's genre NAMES are mapped from. It has no language column either and
# is reused until its expiry, so it can sit in English under ar-SA.
_TMDBH_GENRE_LIST_LANG_BLOCK = (
    "\n"
    "    # -- TMDbHelper genre list language refresh (by ABUKARIM TOOLS) --\n"
    "    # The global genre list is cached without a language. When the language\n"
    "    # changes (or no stamp yet) drop it so it is refetched in the current one.\n"
    "    def create_database(self):\n"
    "        connection = super().create_database()\n"
    "        try:\n"
    "            self._abk_genre_list_language_refresh()\n"
    "        except Exception as error:\n"
    "            self.kodi_log(f'CACHE: ABK genre list language refresh failed: {error}', 1)\n"
    "        return connection\n"
    "\n"
    "    def _abk_genre_list_language_refresh(self):\n"
    "        import sqlite3\n"
    "        from tmdbhelper.lib.addon.plugin import get_language\n"
    "        language = get_language() or 'en-US'\n"
    "        con = sqlite3.connect(self._db_file, timeout=self._db_timeout)\n"
    "        try:\n"
    "            with con:\n"
    "                con.execute('CREATE TABLE IF NOT EXISTS abk_meta(key TEXT PRIMARY KEY, value TEXT)')\n"
    "                row = con.execute(\"SELECT value FROM abk_meta WHERE key='genre_list_language'\").fetchone()\n"
    "                if row and row[0] == language:\n"
    "                    return\n"
    "                cleared = con.execute('DELETE FROM genres').rowcount\n"
    "                con.execute(\"DELETE FROM expiry WHERE id='genres'\")\n"
    "                con.execute(\"INSERT OR REPLACE INTO abk_meta(key, value) VALUES ('genre_list_language', ?)\", (language, ))\n"
    "        finally:\n"
    "            con.close()\n"
    "        self.kodi_log(f'CACHE: ABK genre list language refresh -> {language} ({cleared} genres cleared)', 1)\n"
)







# AF3 50.11.x: the Trailer button's include, restored (3.4.15). See the PATCHES
# entry for Includes_Actions.xml. Link: the item's own trailer, else
# TMDbHelper's, else 'abk://lookup' (trailer_play.py then searches by id).
_AF3_SELECT_TRAILER_BLOCK = (
    '    <!-- ABUKARIM: trailer source (AF3 50.11 dropped this include) -->\n'
    '    <variable name="ABK_Trailer_Link">\n'
    '        <value condition="!String.IsEmpty(ListItem.Trailer)">$INFO[ListItem.Trailer]</value>\n'
    '        <value condition="!String.IsEmpty(Container.ListItem.Trailer)">$INFO[Container.ListItem.Trailer]</value>\n'
    '        <value condition="!String.IsEmpty(Window(Home).Property(TMDbHelper.ListItem.Trailer))">$INFO[Window(Home).Property(TMDbHelper.ListItem.Trailer)]</value>\n'
    '        <value condition="!String.IsEmpty(Window(Home).Property(TMDbHelper.ListItem.base_trailer))">$INFO[Window(Home).Property(TMDbHelper.ListItem.base_trailer)]</value>\n'
    '        <value>abk://lookup</value>\n'
    '    </variable>\n'
    '    <variable name="ABK_Trailer_Title">\n'
    '        <value condition="!String.IsEmpty(ListItem.TVShowTitle)">$INFO[ListItem.TVShowTitle]</value>\n'
    '        <value condition="!String.IsEmpty(ListItem.Title)">$INFO[ListItem.Title]</value>\n'
    '        <value condition="!String.IsEmpty(Container.ListItem.TVShowTitle)">$INFO[Container.ListItem.TVShowTitle]</value>\n'
    '        <value condition="!String.IsEmpty(Container.ListItem.Title)">$INFO[Container.ListItem.Title]</value>\n'
    '        <value condition="!String.IsEmpty(Window(Home).Property(TMDbHelper.ListItem.TVShowTitle))">$INFO[Window(Home).Property(TMDbHelper.ListItem.TVShowTitle)]</value>\n'
    '        <value>$INFO[Window(Home).Property(TMDbHelper.ListItem.Title)]</value>\n'
    '    </variable>\n'
    '    <include name="Action_SelectTrailerSource_OnClick">\n'
    '        <onclick>SetProperty(PlayTrailerItems,$VAR[Path_VideoInfo_Trailers],Home)</onclick>\n'
    '        <onclick>SetProperty(PlayTrailerTitle,$ESCVAR[ABK_Trailer_Title],Home)</onclick>\n'
    '        <onclick>SetProperty(PlayTrailer,$ESCVAR[ABK_Trailer_Link],Home)</onclick>\n'
    '        <onclick>ActivateWindow(1123)</onclick>\n'
    '    </include>\n'
    '\n'
)

# ---------------------------------------------------------------------------
ADDON_NAME  = 'ABUKARIM TOOLS'
HOME        = xbmcvfs.translatePath('special://home/')
ADDONS_DIR  = os.path.join(HOME, 'addons')


def _resolve_addon_dir(addon_id):
    """Folder of an installed add-on, filesystem FIRST.

    3.1.0.12: every sweep used to call xbmcaddon.Addon(<other id>) once per
    patch entry. On Kodi 22 / Python 3.14 (with a broken Addons33.db) that call
    can block inside Kodi's addon manager while holding the Python GIL, which
    freezes every Python add-on at once - the sweep stopped dead after the
    first dexworld entry and the ABUKARIM menu never opened. The standard
    addons/ folder answers in almost every case without touching Kodi; the
    registry is only asked when the folder is absent (portable/non-default
    installs), and a miss is cached for the session.
    """
    local = os.path.join(ADDONS_DIR, addon_id)
    if os.path.isdir(local):
        return local
    if addon_id in _REGISTRY_MISSES:
        return None
    # Silent pre-check: never ask the registry about an id Kodi doesn't know
    # (that call logs "EXCEPTION: Unknown addon id" C++-side).
    if not xbmc.getCondVisibility('System.HasAddon(%s)' % addon_id):
        _REGISTRY_MISSES.add(addon_id)
        return None
    try:
        import xbmcaddon
        path = xbmcvfs.translatePath(xbmcaddon.Addon(addon_id).getAddonInfo('path'))
        if path and os.path.isdir(path):
            return path
    except Exception:
        pass
    _REGISTRY_MISSES.add(addon_id)
    return None


_REGISTRY_MISSES = set()
ADDON_DATA  = xbmcvfs.translatePath('special://profile/addon_data/')

DIALOG      = xbmcgui.Dialog()

# ---------------------------------------------------------------------------
# Patch definitions
# Each entry:
#   addon_id   – folder name under kodi/addons/
#   rel_path   – path to target file relative to addon root
#   old        – exact string to replace
#   new        – replacement string
#   description – shown to user in notifications
# ---------------------------------------------------------------------------

# ── RedLight volume auto-drop kill (by ABUKARIM TOOLS) ──
# RedLight's volume_checker() runs on every playback start and clamps Kodi's player
# volume to redlight.playback.volumecheck_percent (default '50').  On Kodi's
# 0 dB .. -60 dB scale SetVolume(50) lands on -30 dB, so every title starts half
# volume.  The only opt-out is an internal property (volumecheck_enabled) with no
# settings-screen exposure.  Replace the body with an immediate `return`.
_REDLIGHT_VOLCHECKER_OLD_B64 = 'ZGVmIHZvbHVtZV9jaGVja2VyKCk6DQoJIyAwJSA9PSAtNjBkYiwgMTAwJSA9PSAwZGINCgl0cnk6DQoJCWlmIGdldF9wcm9wZXJ0eSgncmVkbGlnaHQucGxheWJhY2sudm9sdW1lY2hlY2tfZW5hYmxlZCcpID09ICdmYWxzZScgb3IgZ2V0X3Zpc2liaWxpdHkoJ1BsYXllci5NdXRlZCcpOiByZXR1cm4NCgkJZnJvbSBtb2R1bGVzLnV0aWxzIGltcG9ydCBzdHJpbmdfYWxwaGFudW1fdG9fbnVtDQoJCW1heF92b2x1bWUgPSBtaW4oaW50KGdldF9wcm9wZXJ0eSgncmVkbGlnaHQucGxheWJhY2sudm9sdW1lY2hlY2tfcGVyY2VudCcpIG9yICc1MCcpLCAxMDApDQoJCWlmIGludCgxMDAgLSAoZmxvYXQoc3RyaW5nX2FscGhhbnVtX3RvX251bShnZXRfaW5mb2xhYmVsKCdQbGF5ZXIuVm9sdW1lJykuc3BsaXQoJy4nKVswXSkpLzYwKSoxMDApID4gbWF4X3ZvbHVtZTogZXhlY3V0ZV9idWlsdGluKCdTZXRWb2x1bWUoJWQpJyAlIG1heF92b2x1bWUpDQoJZXhjZXB0OiBwYXNzDQo='
_REDLIGHT_VOLCHECKER_NEW_B64 = 'ZGVmIHZvbHVtZV9jaGVja2VyKCk6DQoJIyAtLSBSZWRMaWdodCB2b2x1bWUgYXV0by1kcm9wIGRpc2FibGVkIChieSBBQlVLQVJJTSBUT09MUykgLS0NCglyZXR1cm4NCg=='

# ── TMDbHelper Fenlight player (3.2.55) ──
# 3.4.48: "Search All" - one stream list from every add-on (resources/lib/ab_search.py)
_AB_SEARCH_PLAYER_JSON = '{\n    "name": "AB Search All",\n    "plugin": "plugin.program.abukarimtools",\n    "priority": 30,\n    "is_resolvable": false,\n    "play_movie": "executebuiltin://RunPlugin(\\"plugin://plugin.program.abukarimtools/?mode=ab_search&media_type=movie&tmdb_id={id}&imdb={imdb}&year={year}&premiered={premiered}&title={title}\\")",\n    "play_episode": "executebuiltin://RunPlugin(\\"plugin://plugin.program.abukarimtools/?mode=ab_search&media_type=episode&tmdb_id={tmdb}&imdb={imdb}&tvdb={tvdb}&season={season}&episode={episode}&year={year}&premiered={firstaired}&showname={showname}&title={title}\\")"\n}\n'
AB_SEARCH_PLAYER = os.path.join('players', 'abukarim.search_all.json')
_FENLIGHT_PLAYER_JSON = '{\n    "name": "Fenlight",\n    "plugin": "plugin.video.fenlight",\n    "priority": 40,\n    "is_resolvable": false,\n    "play_movie": "executebuiltin://RunPlugin(\\"plugin://plugin.video.fenlight/?mode=playback.media&media_type=movie&query={name}&year={year}&poster={poster}&title={title}&tmdb_id={id}&autoplay=false\\")",\n    "play_episode": "executebuiltin://RunPlugin(\\"plugin://plugin.video.fenlight/?mode=playback.media&media_type=episode&query={showname}&year={year}&season={season}&episode={episode}&ep_name={title}&tmdb_id={tmdb}&premiered={firstaired}&autoplay=false\\")"\n}\n'

# ── Fenlight resolve handoff block (3.2.54, v2) ──
# The "already resolved" set lives in the player module's globals: Kodi's
# xbmc.Player subclasses do not accept class attributes.
_FENLIGHT_HANDOFF_V2 = (
    "\t\t# -- Fenlight resolve handoff v2 (by ABUKARIM TOOLS) --\r\n"
    "\t\t_abk_handed = False\r\n"
    "\t\ttry:\r\n"
    "\t\t\timport sys as _abk_sys, xbmcplugin as _abk_xp\r\n"
    "\t\t\t_abk_h = int(_abk_sys.argv[1]) if len(_abk_sys.argv) > 1 else -1\r\n"
    "\t\t\t_abk_done = globals().setdefault('_ABK_RESOLVED', set())\r\n"
    "\t\t\tif _abk_h >= 0 and _abk_h not in _abk_done:\r\n"
    "\t\t\t\t_abk_done.add(_abk_h)\r\n"
    "\t\t\t\t_abk_xp.setResolvedUrl(_abk_h, True, listing)\r\n"
    "\t\t\t\t_abk_handed = True\r\n"
    "\t\texcept Exception as _abk_e:\r\n"
    "\t\t\t_abk_handed = False\r\n"
    "\t\t\ttry: __import__('xbmc').log('[AbukarimTools] Fenlight handoff failed: %r' % (_abk_e,), 2)\r\n"
    "\t\t\texcept Exception: pass\r\n"
    "\t\tif not _abk_handed: self.play(self.url)\r\n"
)

# ── Fenlight volume auto-drop kill (by ABUKARIM TOOLS) ──
# Fenlight ships the same volume_checker() as RedLight: it runs on every playback
# start and clamps Kodi's player volume to fenlight.playback.volumecheck_percent
# (default '50').  On Kodi's 0 dB .. -60 dB scale SetVolume(50) lands on -30 dB, so
# every title starts at half volume.  Same treatment: replace the body with `return`.
_FENLIGHT_VOLCHECKER_OLD_B64 = 'ZGVmIHZvbHVtZV9jaGVja2VyKCk6DQoJIyAwJSA9PSAtNjBkYiwgMTAwJSA9PSAwZGINCgl0cnk6DQoJCWlmIGdldF9wcm9wZXJ0eSgnZmVubGlnaHQucGxheWJhY2sudm9sdW1lY2hlY2tfZW5hYmxlZCcpID09ICdmYWxzZScgb3IgZ2V0X3Zpc2liaWxpdHkoJ1BsYXllci5NdXRlZCcpOiByZXR1cm4NCgkJZnJvbSBtb2R1bGVzLnV0aWxzIGltcG9ydCBzdHJpbmdfYWxwaGFudW1fdG9fbnVtDQoJCW1heF92b2x1bWUgPSBtaW4oaW50KGdldF9wcm9wZXJ0eSgnZmVubGlnaHQucGxheWJhY2sudm9sdW1lY2hlY2tfcGVyY2VudCcpIG9yICc1MCcpLCAxMDApDQoJCWlmIGludCgxMDAgLSAoZmxvYXQoc3RyaW5nX2FscGhhbnVtX3RvX251bShnZXRfaW5mb2xhYmVsKCdQbGF5ZXIuVm9sdW1lJykuc3BsaXQoJy4nKVswXSkpLzYwKSoxMDApID4gbWF4X3ZvbHVtZTogZXhlY3V0ZV9idWlsdGluKCdTZXRWb2x1bWUoJWQpJyAlIG1heF92b2x1bWUpDQoJZXhjZXB0OiBwYXNzDQo='
_FENLIGHT_VOLCHECKER_NEW_B64 = 'ZGVmIHZvbHVtZV9jaGVja2VyKCk6DQoJIyAtLSBGZW5saWdodCB2b2x1bWUgYXV0by1kcm9wIGRpc2FibGVkIChieSBBQlVLQVJJTSBUT09MUykgLS0NCglyZXR1cm4NCg=='


# ── a4kSubtitles: UTF-8-first decode (by ABUKARIM TOOLS) ──
# a4kSubtitles' download.py __postprocess() re-decodes every subtitle. With
# general.use_chardet ON (the default), an Arabic sub rarely chardet-detects at
# confidence 1.0 / matching lang, so `encoding` stays empty and the code falls
# back to the hardcoded code_pages table -> cp1256 for 'ar'/'ara'. But
# OpenSubtitles.com serves Arabic subs ALREADY as UTF-8, so decoding those bytes
# as cp1256 turns every Arabic glyph into mojibake, then re-saves it as UTF-8 —
# baking in the corruption. (The standalone OpenSubtitles.com addon just writes
# the raw bytes, which is why the same sub looks correct there.) Fix: try UTF-8
# first and only fall back to the legacy code page when UTF-8 actually fails, so
# genuinely-legacy cp1256 files still convert while UTF-8 files are left intact.
_A4KSUBS_DECODE_OLD_B64 = 'ICAgICAgICAgICAgaWYgbm90IGVuY29kaW5nOgogICAgICAgICAgICAgICAgZW5jb2RpbmcgPSBjb3JlLnV0aWxzLmNvZGVfcGFnZXMuZ2V0KGxhbmdfY29kZSwgY29yZS51dGlscy5kZWZhdWx0X2VuY29kaW5nKQoKICAgICAgICAgICAgdGV4dCA9IHRleHRfYnl0ZXMuZGVjb2RlKGVuY29kaW5nKQ=='
_A4KSUBS_DECODE_NEW_B64 = 'ICAgICAgICAgICAgaWYgbm90IGVuY29kaW5nOgogICAgICAgICAgICAgICAgZW5jb2RpbmcgPSBjb3JlLnV0aWxzLmNvZGVfcGFnZXMuZ2V0KGxhbmdfY29kZSwgY29yZS51dGlscy5kZWZhdWx0X2VuY29kaW5nKQoKICAgICAgICAgICAgIyAtLSBhNGtTdWJ0aXRsZXMgVVRGLTgtZmlyc3QgZGVjb2RlIChieSBBQlVLQVJJTSBUT09MUykgLS0KICAgICAgICAgICAgIyBPcGVuU3VidGl0bGVzLmNvbSBzZXJ2ZXMgQXJhYmljIHN1YnMgYWxyZWFkeSBhcyBVVEYtODsgdGhlIG9sZCBjb2RlCiAgICAgICAgICAgICMgZm9yY2VkIHRoZSBsZWdhY3kgY29kZSBwYWdlIChjcDEyNTYgZm9yIGFyKSBhbmQgbWFuZ2xlZCB0aGVtLiBUcnkKICAgICAgICAgICAgIyBVVEYtOCBmaXJzdCBhbmQgb25seSBmYWxsIGJhY2sgdG8gdGhlIGNvZGUgcGFnZSB3aGVuIFVURi04IGZhaWxzLgogICAgICAgICAgICBpZiBlbmNvZGluZyBhbmQgZW5jb2RpbmcubG93ZXIoKS5yZXBsYWNlKCctJywgJycpIG5vdCBpbiAoJ3V0ZjgnLCAndXRmXzgnKToKICAgICAgICAgICAgICAgIHRyeToKICAgICAgICAgICAgICAgICAgICB0ZXh0ID0gdGV4dF9ieXRlcy5kZWNvZGUoJ3V0Zi04JykKICAgICAgICAgICAgICAgICAgICBlbmNvZGluZyA9ICd1dGYtOCcKICAgICAgICAgICAgICAgIGV4Y2VwdCAoVW5pY29kZURlY29kZUVycm9yLCBMb29rdXBFcnJvcik6CiAgICAgICAgICAgICAgICAgICAgdGV4dCA9IHRleHRfYnl0ZXMuZGVjb2RlKGVuY29kaW5nLCBlcnJvcnM9J3JlcGxhY2UnKQogICAgICAgICAgICBlbHNlOgogICAgICAgICAgICAgICAgdGV4dCA9IHRleHRfYnl0ZXMuZGVjb2RlKGVuY29kaW5nIG9yICd1dGYtOCcsIGVycm9ycz0ncmVwbGFjZScp'




# ── AF3: Subtitle Buttons - OSD XML (inserted after the Subtitles button) ──
_AF3_SUBTOOLS_ANCHOR = (
    '                            <param name="groupid">6107</param>\n'
    '                            <param name="itemgap">osd_itemgap</param>\n'
    '                            <param name="iconoffset_condition">[VideoPlayer.SubtitlesEnabled + '
    '!String.IsEmpty(VideoPlayer.SubtitlesLanguage)]</param>\n'
    '                        </include>'
)
_AF3_SUBTOOLS_XML = (
    '\n\n\n'
    '                        <!-- ABUKARIM: AF3 subtitle buttons -->\n'
    '                        <!-- DexSubtitles AutoSync: sync the playing subtitle (autosync.py) -->\n'
    '                        <control type="button" id="6010">\n'
    '                            <include>Defs_OSD_Button</include>\n'
    '                            <visible>System.AddonIsEnabled(service.subtitles.dexworld)</visible>\n'
    '                            <onclick>CancelAlarm(osd_timeout,true)</onclick>\n'
    '                            <onclick>RunScript(special://home/addons/service.subtitles.dexworld/abk_osd_sync.py)</onclick>\n'
    '                        </control>\n'
    '                        <include content="OSD_Button_Icon_Overlay" condition="System.AddonIsEnabled(service.subtitles.dexworld)">\n'
    '                            <param name="icon">$VAR[ABK_LucentIcon_dexsync]</param>\n'
    '                            <param name="id">6010</param>\n'
    '                            <param name="groupid">6110</param>\n'
    '                            <param name="itemgap">osd_itemgap</param>\n'
    '                        </include>\n'
    '\n\n'
    '                        <!-- Subtitle Cycler: next subtitle from every subtitle add-on -->\n'
    '                        <control type="button" id="6011">\n'
    '                            <include>Defs_OSD_Button</include>\n'
    '                            <onclick>CancelAlarm(osd_timeout,true)</onclick>\n'
    '                            <onclick condition="System.AddonIsEnabled(script.subtitle.cycler)">RunScript(script.subtitle.cycler)</onclick>\n'
    '                            <onclick condition="!System.AddonIsEnabled(script.subtitle.cycler)">RunPlugin(plugin://plugin.program.abukarimtools/?mode=subtitle_cycler)</onclick>\n'
    '                        </control>\n'
    '                        <include content="OSD_Button_Icon_Overlay">\n'
    '                            <param name="icon">$VAR[ABK_LucentIcon_subcycler]</param>\n'
    '                            <param name="id">6011</param>\n'
    '                            <param name="groupid">6111</param>\n'
    '                            <param name="itemgap">osd_itemgap</param>\n'
    '                        </include>\n'
    '                        <!-- /ABUKARIM: AF3 subtitle buttons -->'
)

# ── AF3: Subtitle Buttons - matching slots in the OSD popup windows ──
# AF3's stream/info popups (1143/1145/1146/1147/1148/1159) redraw the OSD bar
# from OSD_CustomDialog_GroupList: a right-aligned row of fixed slots 5..9.
# The two new buttons sit between slots 7 and 8 in VideoOSD, so without two
# matching slots here the popup's focused Audio/Subtitle button is drawn two
# slots too far right - a duplicate icon over DexSync/Cycler. Same visibility
# as the real buttons; focusing one closes the popup and moves to the real one.
_AF3_SUBTOOLS_POPUP_ANCHOR = (
    '                <include content="OSD_CustomDialog_FakeButton" condition="![$PARAM[button_8]]">'
)
_AF3_SUBTOOLS_POPUP_XML = (
    '                <!-- ABUKARIM: AF3 subtitle buttons (popup slots) -->\n'
    '                <control type="button" id="6010">\n'
    '                    <width>80</width>\n'
    '                    <texturefocus />\n'
    '                    <texturenofocus />\n'
    '                    <font />\n'
    '                    <label />\n'
    '                    <visible>System.AddonIsEnabled(service.subtitles.dexworld)</visible>\n'
    '                    <onfocus>Close</onfocus>\n'
    '                    <onfocus>SetFocus(6010)</onfocus>\n'
    '                </control>\n'
    '                <control type="button" id="6011">\n'
    '                    <width>80</width>\n'
    '                    <texturefocus />\n'
    '                    <texturenofocus />\n'
    '                    <font />\n'
    '                    <label />\n'
    '                    <onfocus>Close</onfocus>\n'
    '                    <onfocus>SetFocus(6011)</onfocus>\n'
    '                </control>\n'
    '                <!-- /ABUKARIM: AF3 subtitle buttons (popup slots) -->\n\n'
)

# ── TMDbHelper 7.x (4.6.5): the 7.0 rewrite moved what four patches hook ──
# Trakt login now lives in api/trakt/api.py (TraktAPI.login -> poller, a
# DialogProgress), the certification query in items/database/tmdbdata.py,
# and the item database class (ItemDetailsDataBase) only calls
# create_database() when the file is new. The global genre list is already
# cached per language in 7.x (TMDbGenres.db, cache_name GenreLookup.<lang>),
# so the old query/database.py patch has no 7.x counterpart.
_TMDBH7_LOGIN_OLD = (
    "        self.auth_dialog = DialogProgress()\n"
    "        self.auth_dialog.create(get_localized(32097), f'{get_localized(32096)}\\n{get_localized(32095)}: [B]{self.code.get(\"user_code\")}[/B]')\n"
    "        self.poller()\n"
    "\n"
    "    def refresh_token(self):\n"
)
_TMDBH7_LOGIN_NEW = (
    "        # -- TMDbHelper Trakt QR Auth patch v7 (by ABUKARIM TOOLS) --\n"
    "        try:\n"
    "            if self._abk_qr_login():\n"
    "                return\n"
    "        except Exception as exc:\n"
    "            kodi_log(f'Trakt QR login failed, using the stock dialog: {exc}', 1)\n"
    "        self.auth_dialog = DialogProgress()\n"
    "        self.auth_dialog.create(get_localized(32097), f'{get_localized(32096)}\\n{get_localized(32095)}: [B]{self.code.get(\"user_code\")}[/B]')\n"
    "        self.poller()\n"
    "\n"
    "    def _abk_qr_login(self):\n"
    "        \"\"\"Device login in AB Tools' QR window (trakt_auth_qr.xml) instead of\n"
    "        the progress dialog; same polling as poller(). True when it ran.\"\"\"\n"
    "        import xbmcaddon as _xbmcaddon\n"
    "        from xbmc import Monitor\n"
    "        from tmdbhelper.lib.api.trakt.qr_utils import make_qr, remove_qr, get_qr_dialog\n"
    "        user_code = str(self.code.get('user_code'))\n"
    "        qr_path = make_qr('https://trakt.tv/activate/' + user_code)\n"
    "        addon_path = _xbmcaddon.Addon('plugin.video.themoviedb.helper').getAddonInfo('path')\n"
    "        expires_in = int(self.expires_in or 0)\n"
    "        qr_dialog = get_qr_dialog(addon_path)\n"
    "        qr_dialog.show()\n"
    "        qr_dialog.setProperty('user_code', user_code)\n"
    "        qr_dialog.setProperty('qr_image', qr_path)\n"
    "        qr_dialog.setProperty('progress_width', '530')\n"
    "        qr_dialog.setProperty('expires_label', 'Expires in %ss' % expires_in)\n"
    "        monitor = Monitor()\n"
    "        try:\n"
    "            while not monitor.abortRequested():\n"
    "                if getattr(qr_dialog, 'is_canceled', False):\n"
    "                    kodi_log(u'Trakt authentication aborted!', 1)\n"
    "                    break\n"
    "                self.progress += self.interval\n"
    "                remaining = max(expires_in - self.progress, 0)\n"
    "                width = int(float(remaining * 530) / expires_in) if expires_in else 0\n"
    "                qr_dialog.setProperty('progress_width', str(width))\n"
    "                qr_dialog.setProperty('expires_label', 'Expires in %ss' % remaining)\n"
    "                if expires_in <= self.progress:\n"
    "                    kodi_log(u'Trakt authentication expired!', 1)\n"
    "                    break\n"
    "                self.authorization = self.get_api_request_json('https://api.trakt.tv/oauth/device/token', postdata={'code': self.code.get('device_code'), 'client_id': self.client_id, 'client_secret': self.client_secret})\n"
    "                if self.authorization:\n"
    "                    self.on_authenticated(auth_dialog=False)\n"
    "                    break\n"
    "                monitor.waitForAbort(self.interval)\n"
    "        finally:\n"
    "            try:\n"
    "                qr_dialog.close()\n"
    "            except Exception:\n"
    "                pass\n"
    "            del qr_dialog\n"
    "            remove_qr(qr_path)\n"
    "        return True\n"
    "        # -- end TMDbHelper Trakt QR Auth patch v7 --\n"
    "\n"
    "    def refresh_token(self):\n"
)

_TMDBH7_CERT_OLD = (
    "class CertificationDetailsDataBaseCache(ItemDetailsListDataBaseCache):\n"
    "    table = 'certification'\n"
    "    keys = ('name', 'iso_country', 'iso_language', 'release_date', 'release_type', 'parent_id', )\n"
    "    conditions = 'parent_id=? AND iso_country=? ORDER BY release_date ASC LIMIT 1'  # WHERE conditions\n"
    "\n"
    "    @property\n"
    "    def values(self):  # WHERE conditions values for ?\n"
    "        return (self.item_id, self.tmdb_api.iso_country)\n"
)
_TMDBH7_CERT_NEW = (
    "class CertificationDetailsDataBaseCache(ItemDetailsListDataBaseCache):\n"
    "    # -- USA certification fallback v7 (by ABUKARIM TOOLS) --\n"
    "    table = 'certification'\n"
    "    keys = ('name', 'iso_country', 'iso_language', 'release_date', 'release_type', 'parent_id', )\n"
    "    conditions = 'parent_id=? AND iso_country IN (?, \"US\") AND name IS NOT NULL AND name != \"\" ORDER BY iso_country=? DESC, IFNULL(release_date, \"9999-99-99\") ASC LIMIT 1'  # WHERE conditions\n"
    "\n"
    "    @property\n"
    "    def values(self):  # WHERE conditions values for ?\n"
    "        iso_country = self.tmdb_api.iso_country\n"
    "        return (self.item_id, iso_country, iso_country)\n"
)

_TMDBH7_GENRE_ANCHOR = "class ItemDetailsDataBase(DataBase):\n"
_TMDBH7_GENRE_BLOCK = (
    "\n"
    "    # -- TMDbHelper genre language refresh v7 (by ABUKARIM TOOLS) --\n"
    "    # Genre rows carry no language and are never overwritten, so after a\n"
    "    # language change they stay in the old language. Once per Kodi session\n"
    "    # (and language): clear them and expire their items so they are\n"
    "    # refetched in the current language. 7.x only calls create_database()\n"
    "    # for a new file, so this runs after the initialisation check instead.\n"
    "    def check_database_initialization(self):\n"
    "        super().check_database_initialization()\n"
    "        try:\n"
    "            self._abk_genre_language_refresh()\n"
    "        except Exception as error:\n"
    "            self.kodi_log(f'CACHE: ABK genre language refresh failed: {error}', 1)\n"
    "\n"
    "    def _abk_genre_language_refresh(self):\n"
    "        import sqlite3\n"
    "        import xbmcvfs\n"
    "        from tmdbhelper.lib.addon.plugin import get_language\n"
    "        language = get_language() or 'en-US'\n"
    "        prop = 'ABK.GenreLanguage.Checked'\n"
    "        if self.get_window_property(prop) == language:\n"
    "            return\n"
    "        if not xbmcvfs.exists(self._db_file):\n"
    "            return\n"
    "        cleared = 0\n"
    "        con = sqlite3.connect(self._db_file, timeout=self._db_timeout)\n"
    "        try:\n"
    "            with con:\n"
    "                con.execute('CREATE TABLE IF NOT EXISTS abk_meta(key TEXT PRIMARY KEY, value TEXT)')\n"
    "                row = con.execute(\"SELECT value FROM abk_meta WHERE key='genre_language_v2'\").fetchone()\n"
    "                if not row or row[0] != language:\n"
    "                    con.execute('UPDATE baseitem SET expiry=0 WHERE id IN (SELECT parent_id FROM genre)')\n"
    "                    cleared = con.execute('DELETE FROM genre').rowcount\n"
    "                    con.execute(\"INSERT OR REPLACE INTO abk_meta(key, value) VALUES ('genre_language_v2', ?)\", (language, ))\n"
    "        finally:\n"
    "            con.close()\n"
    "        self.set_window_property(prop, language)\n"
    "        if cleared:\n"
    "            self.kodi_log(f'CACHE: ABK genre language refresh -> {language} ({cleared} genre rows cleared)', 1)\n"
    "\n"
)

# ── AF3: Subtitle Look button (4.6.2, toggle 'af3_substyle') ──
# One OSD button just before Video settings (6008): opens AB Tools' subtitle
# panel (sub_quick.py) - 4.6.27: Dex Hub's whole subtitle look (rows, looks, swatches).
_AF3_SUBSTYLE_ANCHOR = '                        <control type="button" id="6008">'
_AF3_SUBSTYLE_XML = (
    '                        <!-- ABUKARIM: AF3 subtitle look button -->\n'
    '                        <control type="button" id="6012">\n'
    '                            <include>Defs_OSD_Button</include>\n'
    '                            <onclick>CancelAlarm(osd_timeout,true)</onclick>\n'
    '                            <onclick>RunPlugin(plugin://plugin.program.abukarimtools/?mode=subtitle_style)</onclick>\n'
    '                        </control>\n'
    '                        <include content="OSD_Button_Icon_Overlay">\n'
    '                            <param name="icon">$VAR[ABK_LucentIcon_substyle]</param>\n'
    '                            <param name="id">6012</param>\n'
    '                            <param name="groupid">6112</param>\n'
    '                            <param name="itemgap">osd_itemgap</param>\n'
    '                        </include>\n'
    '                        <!-- /ABUKARIM: AF3 subtitle look button -->\n\n\n'
)
# Matching empty slot in the OSD popups (1143-1159), so their redrawn bar
# keeps the same number of slots as VideoOSD (no shifted duplicate icon).
_AF3_SUBSTYLE_POPUP_XML = (
    '                <!-- ABUKARIM: AF3 subtitle look button (popup slot) -->\n'
    '                <control type="button" id="6012">\n'
    '                    <width>80</width>\n'
    '                    <texturefocus />\n'
    '                    <texturenofocus />\n'
    '                    <font />\n'
    '                    <label />\n'
    '                    <onfocus>Close</onfocus>\n'
    '                    <onfocus>SetFocus(6012)</onfocus>\n'
    '                </control>\n'
    '                <!-- /ABUKARIM: AF3 subtitle look button (popup slot) -->\n\n'
)


PATCHES = [
    # ── TMDbHelper Trakt QR Auth (by ABUKARIM TOOLS) ──
    {
        'addon_id': 'plugin.video.themoviedb.helper',
        'rel_path': os.path.join('resources', 'tmdbhelper', 'lib', 'api', 'trakt', 'qr_utils.py'),
        'old': '', 'new': '',
        'description': 'TMDbHelper - inject qr_utils.py',
        'inject_file': True,
        'inject_content_b64': _TMDBH_QR_UTILS_B64,
        'already_patched_check': 'api.qrserver.com',
    },
    {
        'addon_id': 'plugin.video.themoviedb.helper',
        'rel_path': os.path.join('resources', 'skins', 'Default', '1080i', 'trakt_auth_qr.xml'),
        'old': '', 'new': '',
        'description': 'TMDbHelper - inject trakt_auth_qr.xml',
        'inject_file': True,
        'inject_content_b64': _TMDBH_TRAKT_XML_B64,
        'already_patched_check': 'Trakt Authentication',
    },
    # trakt_auth_qr.xml is loaded as a WindowXMLDialog from TMDbHelper's OWN skin
    # folder (get_qr_dialog -> WindowXMLDialog('trakt_auth_qr.xml', addon_path,
    # 'Default', '1080i')), so bare texture names resolve against that addon skin's
    # media dir — NOT the active Kodi skin. TMDbHelper ships no white.png there, so
    # every <texture background="true">white.png</texture> fill (dim overlay, dark
    # card, green bar, dividers, code box, progress bar) failed to load
    # ("CGUITextureManager::GetTexturePath: could not find texture 'white.png'"),
    # leaving only the labels + self-white QR floating over the un-dimmed live
    # background. Ship a solid-opaque white.png so all the colordiffuse fills paint.
    # Same binary inject_source + replace + byte-compare idempotency as the badges.
    {
        'addon_id': 'plugin.video.themoviedb.helper',
        'rel_path': os.path.join('resources', 'skins', 'Default', 'media', 'white.png'),
        'inject_file': True,
        'binary': True,
        'replace': True,
        'inject_source': os.path.join('resources', 'tmdbhelper_qr', 'white.png'),
        'description': 'TMDbHelper - inject white.png (QR dialog fill texture)',
    },
    {
        'addon_id': 'plugin.video.themoviedb.helper',
        'rel_path': os.path.join('resources', 'tmdbhelper', 'lib', 'api', 'trakt', 'authenticator.py'),
        'old': base64.b64decode(_TMDBH_POLLER_OLD_B64).decode('utf-8'),
        'new': base64.b64decode(_TMDBH_POLLER_NEW_B64).decode('utf-8'),
        'description': 'TMDbHelper authenticator.py - Trakt QR auth dialog',
        'max_version': '6.99.99',          # 7.x: see the v7 entry below
        'already_patched_check': '# -- TMDbHelper Trakt QR Auth patch (by ABUKARIM TOOLS) --',
        # Version-resilient fallback: replace the whole poller() method by anchor,
        # regardless of minor whitespace/line drift between TMDbHelper releases.
        'fallback_pattern': r'    def poller\(self\):\n[\s\S]*?\n(?=    mutex_lockname)',
        'fallback_repl': (lambda _b: (lambda m: base64.b64decode(_b).decode('utf-8') + '\n'))(_TMDBH_POLLER_NEW_B64),
    },
    {
        'addon_id': 'plugin.video.themoviedb.helper',
        'rel_path': os.path.join('resources', 'tmdbhelper', 'lib', 'api', 'trakt', 'api.py'),
        'toggle': 'tmdbh_trakt_auth',
        'min_version': '7.0.0',
        'old': _TMDBH7_LOGIN_OLD,
        'new': _TMDBH7_LOGIN_NEW,
        'already_patched_check': '# -- TMDbHelper Trakt QR Auth patch v7 (by ABUKARIM TOOLS) --',
        'description': 'TMDbHelper 7 api.py - Trakt QR auth dialog',
    },
    # ── TMDbHelper – fall back to the USA certification (MPAA) ──
    # Applies to movies AND tv: release_dates (movies) and content_ratings (tv) are both
    # stored in the one 'certification' table keyed by iso_country, and this single query
    # reads it for both. Preference order is preserved: if the configured country DOES
    # have a certification for the title it still wins (ORDER BY iso_country=? DESC);
    # the US row is only used when the configured country has none. US users unaffected.
    # No cache flush needed — the US rows are already in Reference.db from the first fetch.
    {
        'addon_id': 'plugin.video.themoviedb.helper',
        'rel_path': os.path.join('resources', 'tmdbhelper', 'lib', 'items', 'database',
                                 'basemeta_factories', 'concrete_classes', 'info.py'),
        'old': base64.b64decode(_TMDBH_CERTFALLBACK_OLD_B64).decode('utf-8'),
        'new': base64.b64decode(_TMDBH_CERTFALLBACK_NEW_B64).decode('utf-8'),
        'description': 'TMDbHelper info.py - use the USA certification when the configured country (e.g. SA) has none',
        'max_version': '6.99.99',          # 7.x: see the v7 entry below
        'already_patched_check': '# -- USA certification fallback (by ABUKARIM TOOLS) --',
        'fallback_pattern': r"conditions = 'parent_id=\? AND iso_country=\? AND name IS NOT NULL",
        'fallback_repl': (
            'conditions = \'parent_id=? AND iso_country IN (?, \"US\") AND name IS NOT NULL'
        ),
    },
    {
        'addon_id': 'plugin.video.themoviedb.helper',
        'rel_path': os.path.join('resources', 'tmdbhelper', 'lib', 'items', 'database', 'tmdbdata.py'),
        'toggle': 'tmdbh_mpaa_ksa',
        'min_version': '7.0.0',
        'old': _TMDBH7_CERT_OLD,
        'new': _TMDBH7_CERT_NEW,
        'already_patched_check': '# -- USA certification fallback v7 (by ABUKARIM TOOLS) --',
        'description': 'TMDbHelper 7 tmdbdata.py - use the USA certification when the configured country (e.g. SA) has none',
    },
    # ── RedLight – kill automatic volume drop to -30 dB on playback start ──
    {
        'addon_id': 'plugin.video.redlight',
        'rel_path': os.path.join('resources', 'lib', 'modules', 'kodi_utils.py'),
        'old': base64.b64decode(_REDLIGHT_VOLCHECKER_OLD_B64).decode('utf-8'),
        'new': base64.b64decode(_REDLIGHT_VOLCHECKER_NEW_B64).decode('utf-8'),
        'description': 'RedLight kodi_utils.py - disable auto volume drop to -30 dB on every playback',
        'already_patched_check': '-- RedLight volume auto-drop disabled (by ABUKARIM TOOLS) --',
        'fallback_pattern': r'def volume_checker\(\):[\s\S]*?except:\s*pass',
        'fallback_repl': ("def volume_checker():\r\n"
                          "\t# -- RedLight volume auto-drop disabled (by ABUKARIM TOOLS) --\r\n"
                          "\treturn"),
    },
    # ── Fenlight – kill automatic volume drop to -30 dB on playback start ──
    {
        'addon_id': 'plugin.video.fenlight',
        'rel_path': os.path.join('resources', 'lib', 'modules', 'kodi_utils.py'),
        'old': base64.b64decode(_FENLIGHT_VOLCHECKER_OLD_B64).decode('utf-8'),
        'new': base64.b64decode(_FENLIGHT_VOLCHECKER_NEW_B64).decode('utf-8'),
        'description': 'Fenlight kodi_utils.py - disable auto volume drop to -30 dB on every playback',
        'already_patched_check': '-- Fenlight volume auto-drop disabled (by ABUKARIM TOOLS) --',
        'fallback_pattern': r'def volume_checker\(\):[\s\S]*?except:\s*pass',
        'fallback_repl': ("def volume_checker():\r\n"
                          "\t# -- Fenlight volume auto-drop disabled (by ABUKARIM TOOLS) --\r\n"
                          "\treturn"),
    },
    # ── Fenlight – resolve handoff for TMDbHelper (3.2.53) ──
    # TMDbHelper's Fenlight player resolves plugin://plugin.video.fenlight/?mode=
    # playback.media, so Kodi waits on a resolve handle. Fenlight never answers
    # it: it plays the debrid link itself with xbmc.Player().play(), so the
    # handle stays pending for the whole film and fails when the script exits
    # ("ResolvePath(): ... is not playable" -> "Playback failed" dialog at stop).
    # With is_resolvable=false the old player JSON played it via xbmc.Player()
    # instead, which froze Kodi at sources_results (nested plugin resolve on the
    # GUI thread + Python 3.14 GIL). Fix: when Fenlight runs with a live handle
    # (sys.argv[1] >= 0) it hands the link back with setResolvedUrl, once per
    # handle; Fenlight's own menus (handle -1) still use self.play(). The
    # monitor loop is unchanged - it watches whatever the player is playing.
    {
        'addon_id': 'plugin.video.fenlight',
        'rel_path': os.path.join('resources', 'lib', 'modules', 'player.py'),
        'toggle': 'fenlight_tmdbh',
        'old': ("\t\tlisting = self.make_listing()\r\n"
                "\t\tself.play(self.url)\r\n"),
        'new': "\t\tlisting = self.make_listing()\r\n" + _FENLIGHT_HANDOFF_V2,
        'already_patched_check': '# -- Fenlight resolve handoff v2 (by ABUKARIM TOOLS) --',
        # 3.2.54: upgrade a v1 block in place (v1 stored its "already
        # resolved" set on the FenLightPlayer class; xbmc.Player subclasses
        # refuse class attributes -> AttributeError -> silent fallback to
        # self.play(), so v1 never handed anything over).
        'fallback_pattern': (r'\t\t# -- Fenlight resolve handoff \(by ABUKARIM TOOLS\) --\r?\n'
                             r'[\s\S]*?self\.play\(self\.url\)[^\r\n]*\r?\n'),
        'fallback_repl': lambda _m: _FENLIGHT_HANDOFF_V2,
        'description': 'Fenlight player.py - answer the TMDbHelper resolve with setResolvedUrl (no freeze, no "Playback failed" at stop)',
    },
    # ── TMDbHelper – pin the Fenlight player JSON (3.2.55) ──
    # executebuiltin://RunPlugin(...): TMDbHelper first closes its own handle
    # with dummy.mp4, then runs Fenlight as a plain plugin (handle -1), the same
    # way as opening Fenlight directly. No plugin-inside-plugin resolve: the
    # resolvable variant (3.2.53) still deadlocked the GUI thread at random
    # while Fenlight started; the xbmc.Player() variant froze at sources.
    # Content-compared inject: rewritten only if something reverts it.
    {
        'addon_id': 'plugin.video.themoviedb.helper',
        'base': 'addon_data',
        'rel_path': os.path.join('players', 'direct.fenlight.select.json'),
        'toggle': 'fenlight_tmdbh',
        'inject_file': True,
        'old': '',
        'new': '',
        'inject_content': _FENLIGHT_PLAYER_JSON,
        'description': 'TMDbHelper players/direct.fenlight.select.json - Fenlight via dummy + RunPlugin (no nested resolve)',
    },

    # ── a4kSubtitles – decode Arabic (and other) subtitles as UTF-8 first ──
    # Fixes OpenSubtitles.com Arabic subs showing as mojibake in a4kSubtitles
    # while the standalone OpenSubtitles.com addon shows them correctly. See the
    # blob comment above: __postprocess() forced cp1256 on already-UTF-8 subs.
    {
        'addon_id': 'service.subtitles.a4ksubtitles',
        'rel_path': os.path.join('a4kSubtitles', 'download.py'),
        'old': base64.b64decode(_A4KSUBS_DECODE_OLD_B64).decode('utf-8'),
        'new': base64.b64decode(_A4KSUBS_DECODE_NEW_B64).decode('utf-8'),
        'description': 'a4kSubtitles download.py - decode subtitles as UTF-8 first (fixes OpenSubtitles.com Arabic mojibake)',
        'already_patched_check': '# -- a4kSubtitles UTF-8-first decode (by ABUKARIM TOOLS) --',
        'not_found_ok': True,
        'toggle': 'a4ksubs_utf8',
    },

    # ── RedLight – dark fallback for the sources window (group 'redlight') ──
    # Root cause: sources_results.xml paints every row pill and the poster panel with
    #   <texture colordiffuse="$INFO[Window(10000).Property(redlight.window_theme[.sources])]"
    #            border="30">redlight_common/circle.png</texture>
    # circle.png is a WHITE texture. When that window property is empty Kodi applies no
    # diffuse at all and the white texture renders as-is - which is the "light background".
    # It is not a light theme, it is the theme colour going missing, so it comes and goes
    # depending on whether RedLight has written the property by the time the window loads
    # (kodi.log shows the open taking anywhere from 0.6s to 11.9s, and
    # "Control 2000 in window 13002 has been asked to focus, but it can't" on every open).
    # Fix is deterministic and race-proof: after each themed image control, add a twin that
    # is visible ONLY while the property is empty and is hard-coded to the correct dark
    # value (FF232424, sampled from a known-good render). Later controls draw on top, so
    # the stray white is covered. When the property IS set the twin stays hidden and the
    # add-on's own theming is untouched.
    {
        'addon_id': 'plugin.video.redlight',
        'rel_path': os.path.join('resources', 'skins', 'Default', '1080i', 'sources_results.xml'),
        'old': '',   # regex-only: one entry covers all four sites
        'new': '',
        'count': 0,  # 0 -> re.subn replaces every match
        'description': 'RedLight sources_results.xml - dark fallback when the window theme property is empty (kills the intermittent white background)',
        # Lucent replaces this window entirely (no circle.png pills left to fix).
        'obsolete_if_contains': '<!-- LUCENT for ',
        'already_patched_check': '<!-- ABUKARIM: dark fallback when the theme property is empty -->',
        'fallback_pattern': (
            r'([ \t]*)<control type="image">(\r?\n)'
            r'((?:[ \t]*<(?:left|top|width|height)>[^<]*</(?:left|top|width|height)>\r?\n)+)'
            r'([ \t]*)<texture colordiffuse="\$INFO\[Window\(10000\)\.Property\('
            r'(redlight\.window_theme(?:\.sources)?)\)\]" border="30">'
            r'redlight_common/circle\.png</texture>\r?\n'
            r'([ \t]*)</control>'
        ),
        'fallback_repl': (
            lambda m: (
                m.group(0) + m.group(2)
                + m.group(1) + '<!-- ABUKARIM: dark fallback when the theme property is empty -->' + m.group(2)
                + m.group(1) + '<control type="image">' + m.group(2)
                + m.group(3)
                + m.group(4) + '<texture colordiffuse="FF232424" border="30">redlight_common/circle.png</texture>' + m.group(2)
                + m.group(4) + '<visible>String.IsEmpty(Window(10000).Property(' + m.group(5) + '))</visible>' + m.group(2)
                + m.group(6) + '</control>'
            )
        ),
    },

    # ── TinyPPI – replace the SDR/HDR10/HDR10+ codec badge graphics ──
    # Binary texture swap: overwrite the three HDR-badge PNGs in the overlay's
    # media/codecs folder with ABUKARIM TOOLS artwork. Shipped as real files
    # under resources/tinyppi_codecs/ (not inline base64) and written verbatim.
    # 'replace': True overwrites the stock art; the byte-compare in _apply_patch
    # makes it idempotent (a re-run / watchdog sweep skips once installed).
    {
        'addon_id': 'script.tinyppi',
        'rel_path': os.path.join('resources', 'skins', 'Default', 'media', 'codecs', 'SDR.png'),
        'inject_file': True,
        'binary': True,
        'replace': True,
        'inject_source': os.path.join('resources', 'tinyppi_codecs', 'SDR.png'),
        'description': 'TinyPPI codecs - replace SDR.png badge',
    },
    {
        'addon_id': 'script.tinyppi',
        'rel_path': os.path.join('resources', 'skins', 'Default', 'media', 'codecs', 'HDR10.png'),
        'inject_file': True,
        'binary': True,
        'replace': True,
        'inject_source': os.path.join('resources', 'tinyppi_codecs', 'HDR10.png'),
        'description': 'TinyPPI codecs - replace HDR10.png badge',
    },
    {
        'addon_id': 'script.tinyppi',
        'rel_path': os.path.join('resources', 'skins', 'Default', 'media', 'codecs', 'HDR10Plus.png'),
        'inject_file': True,
        'binary': True,
        'replace': True,
        'inject_source': os.path.join('resources', 'tinyppi_codecs', 'HDR10Plus.png'),
        'description': 'TinyPPI codecs - replace HDR10Plus.png badge',
    },

    # ── TinyPPI – replace the Dolby audio codec badge graphics ──
    # Same binary texture-swap mechanism as the HDR badges above (inject_source
    # + replace + byte-compare idempotency). Five Dolby audio badges shipped as
    # real files under resources/tinyppi_codecs/ and written verbatim.
    {
        'addon_id': 'script.tinyppi',
        'rel_path': os.path.join('resources', 'skins', 'Default', 'media', 'codecs', 'Dolby_Digital.png'),
        'inject_file': True,
        'binary': True,
        'replace': True,
        'inject_source': os.path.join('resources', 'tinyppi_codecs', 'Dolby_Digital.png'),
        'description': 'TinyPPI codecs - replace Dolby_Digital.png badge',
    },
    {
        'addon_id': 'script.tinyppi',
        'rel_path': os.path.join('resources', 'skins', 'Default', 'media', 'codecs', 'Dolby_Digital_Plus.png'),
        'inject_file': True,
        'binary': True,
        'replace': True,
        'inject_source': os.path.join('resources', 'tinyppi_codecs', 'Dolby_Digital_Plus.png'),
        'description': 'TinyPPI codecs - replace Dolby_Digital_Plus.png badge',
    },
    {
        'addon_id': 'script.tinyppi',
        'rel_path': os.path.join('resources', 'skins', 'Default', 'media', 'codecs', 'Dolby_Digital_Plus_Atmos.png'),
        'inject_file': True,
        'binary': True,
        'replace': True,
        'inject_source': os.path.join('resources', 'tinyppi_codecs', 'Dolby_Digital_Plus_Atmos.png'),
        'description': 'TinyPPI codecs - replace Dolby_Digital_Plus_Atmos.png badge',
    },
    {
        'addon_id': 'script.tinyppi',
        'rel_path': os.path.join('resources', 'skins', 'Default', 'media', 'codecs', 'Dolby_TrueHD.png'),
        'inject_file': True,
        'binary': True,
        'replace': True,
        'inject_source': os.path.join('resources', 'tinyppi_codecs', 'Dolby_TrueHD.png'),
        'description': 'TinyPPI codecs - replace Dolby_TrueHD.png badge',
    },
    {
        'addon_id': 'script.tinyppi',
        'rel_path': os.path.join('resources', 'skins', 'Default', 'media', 'codecs', 'Dolby_TrueHD_Atmos.png'),
        'inject_file': True,
        'binary': True,
        'replace': True,
        'inject_source': os.path.join('resources', 'tinyppi_codecs', 'Dolby_TrueHD_Atmos.png'),
        'description': 'TinyPPI codecs - replace Dolby_TrueHD_Atmos.png badge',
    },

    # ── PPI AF3: legacy Arctic Fuse 3 DialogPlayerProcessInfo (native) ─
    # AF3 5.7.x REWROTE its PlayerProcessInfo into a list dialog and DROPPED the
    # old PPI_Classic/PPI_Modern variant system. We ship the legacy dialog (from
    # AF3 5.4.28) + its includes as whole FILES the skin gains, plus ONE
    # registration line in Includes.xml. All vars read native Kodi
    # Player.Process/VideoPlayer infolabels. 3.2.40: the TinyPPI Home bridge
    # (home_publish.py + monitor.py hook) is retired - it ran a full TinyPPI read
    # pass every second during playback; the Bridge* skin vars fall back to the
    # native infolabels, and _cleanup_retired_tinyppi() removes the old files.
    # Bundling Includes_p3i also fixes the "invalid include: CodecLogos*/*_Flag"
    # log warnings 5.7.x left behind. All under toggle 'ppi_af3'; not_found_ok
    # so a missing skin is a clean skip.
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'DialogPlayerProcessInfo.xml'),
        'toggle': 'ppi_af3',
        'inject_file': True,
        'binary': True,
        'replace': True,
        'not_found_ok': True,
        'inject_source': os.path.join('resources', 'ppi_af3', 'skin_legacy',
                                      'DialogPlayerProcessInfo.xml'),
        'description': 'PPI AF3 - legacy DialogPlayerProcessInfo.xml',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes_PPI_Classic.xml'),
        'toggle': 'ppi_af3',
        'inject_file': True,
        'binary': True,
        'replace': True,
        'not_found_ok': True,
        'inject_source': os.path.join('resources', 'ppi_af3', 'skin_legacy',
                                      'Includes_PPI_Classic.xml'),
        'description': 'PPI AF3 - legacy Includes_PPI_Classic.xml',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes_PPI_Modern.xml'),
        'toggle': 'ppi_af3',
        'inject_file': True,
        'binary': True,
        'replace': True,
        'not_found_ok': True,
        'inject_source': os.path.join('resources', 'ppi_af3', 'skin_legacy',
                                      'Includes_PPI_Modern.xml'),
        'description': 'PPI AF3 - legacy Includes_PPI_Modern.xml',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes_PPI_Legacy_Support.xml'),
        'toggle': 'ppi_af3',
        'inject_file': True,
        'binary': True,
        'replace': True,
        'not_found_ok': True,
        'inject_source': os.path.join('resources', 'ppi_af3', 'skin_legacy',
                                      'Includes_PPI_Legacy_Support.xml'),
        'description': 'PPI AF3 - legacy PPI variable defs + Part_ChartButton',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes_p3i.xml'),
        'toggle': 'ppi_af3',
        'inject_file': True,
        'binary': True,
        'replace': True,
        'not_found_ok': True,
        'inject_source': os.path.join('resources', 'ppi_af3', 'skin_legacy',
                                      'Includes_p3i.xml'),
        'description': 'PPI AF3 - legacy Includes_p3i.xml (codec logos + flags)',
    },
    {
        # Register the 5 legacy includes. One idempotent string-inject after the
        # existing Includes_Labels.xml registration.
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes.xml'),
        'toggle': 'ppi_af3',
        'not_found_ok': True,
        'old': '    <include file="Includes_Labels.xml" />',
        'new': ('    <include file="Includes_Labels.xml" />\n'
                '    <include file="Includes_PPI_Legacy_Support.xml" />  <!-- ABUKARIM: PPI AF3 -->\n'
                '    <include file="Includes_PPI_Classic.xml" />  <!-- ABUKARIM: PPI AF3 -->\n'
                '    <include file="Includes_PPI_Modern.xml" />  <!-- ABUKARIM: PPI AF3 -->\n'
                '    <include file="Includes_p3i.xml" />  <!-- ABUKARIM: PPI AF3 -->'),
        'already_patched_check': 'Includes_PPI_Legacy_Support.xml',
        'fallback_pattern': r'(<include file="Includes_Labels\.xml" />)',
        'fallback_repl': (r'\1\n    <include file="Includes_PPI_Legacy_Support.xml" />  <!-- ABUKARIM: PPI AF3 -->'
                          r'\n    <include file="Includes_PPI_Classic.xml" />  <!-- ABUKARIM: PPI AF3 -->'
                          r'\n    <include file="Includes_PPI_Modern.xml" />  <!-- ABUKARIM: PPI AF3 -->'
                          r'\n    <include file="Includes_p3i.xml" />  <!-- ABUKARIM: PPI AF3 -->'),
        'description': 'PPI AF3 - register legacy PPI includes',
    },

    # ── AF3: no artwork "Preview" button in the ABUKARIM pickers ──
    # AF3 shows a Preview (معاينة) side button on every DETAILED select list
    # (control 6). In the Trakt Lists pickers it only enlarges the add-on's
    # own icon. Hide it ONLY while Window(Home).Property(abk.nopreview) is set
    # (trakt_hubs sets it around its pickers); all other dialogs unchanged.
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Dialog_DialogSelect.xml'),
        'not_found_ok': True,
        'old': ('            <param name="icon">special://skin/extras/icons/images.png</param>\n'
                '            <visible>Control.IsEnabled(6) + Control.IsVisible(6)</visible>'),
        'new': ('            <param name="icon">special://skin/extras/icons/images.png</param>\n'
                '            <visible>Control.IsEnabled(6) + Control.IsVisible(6) + '
                'String.IsEmpty(Window(Home).Property(abk.nopreview))</visible>'),
        'already_patched_check': 'Window(Home).Property(abk.nopreview)',
        'fallback_pattern': (r'(<param name="id">9004</param>[\s\S]{0,400}?'
                             r'<visible>Control\.IsEnabled\(6\) \+ Control\.IsVisible\(6\))(</visible>)'),
        'fallback_repl': r'\1 + String.IsEmpty(Window(Home).Property(abk.nopreview))\2',
        'description': 'AF3 - no Preview button in the ABUKARIM Trakt Lists pickers',
    },

    # ── AF3: Vertical Plot on Home (by ABUKARIM TOOLS) ──
    # AF3 draws the Info_Panel plot as a "fake box" (a wrapmultiline LABEL)
    # unless Skin.HasSetting(Textboxes.DisableFakeBox). A label cannot scroll
    # vertically, and with Labels.Autoscroll on it marquees HORIZONTALLY.
    # AF2 uses a real textbox (vertical autoscroll). Passing use_textbox=true
    # to the two Home Info_Panel calls (Hub_Combined_Info plot panel + the
    # Spotlight panel) switches ONLY the Home plot to a real textbox; the rest
    # of the skin and the "Use fake textbox" setting are untouched.
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes_Hubs.xml'),
        'toggle': 'af3_vplot',
        'not_found_ok': True,
        'old': '<param name="include_title">false</param>',
        'new': ('<param name="include_title">false</param>\n'
                '                    <param name="use_textbox">true</param>  <!-- ABUKARIM: vertical plot (hub) -->'),
        'already_patched_check': '<!-- ABUKARIM: vertical plot (hub) -->',
        'fallback_pattern': r'(<param name="include_title">false</param>)',
        'fallback_repl': r'\1\n                    <param name="use_textbox">true</param>  <!-- ABUKARIM: vertical plot (hub) -->',
        'description': 'AF3 - Home hub plot scrolls vertically (textbox)',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes_Hubs.xml'),
        'toggle': 'af3_vplot',
        'not_found_ok': True,
        'old': '<param name="container">Container(301).</param>',
        'new': ('<param name="container">Container(301).</param>\n'
                '                <param name="use_textbox">true</param>  <!-- ABUKARIM: vertical plot (spotlight) -->'),
        'already_patched_check': '<!-- ABUKARIM: vertical plot (spotlight) -->',
        'fallback_pattern': r'(<param name="container">Container\(301\)\.</param>)',
        'fallback_repl': r'\1\n                <param name="use_textbox">true</param>  <!-- ABUKARIM: vertical plot (spotlight) -->',
        'description': 'AF3 - Home spotlight plot scrolls vertically (textbox)',
    },

    # ── AF3: Vertical Plot — smaller plot font on Home (font_mini_plot) ──
    # Info_Plot_TextBox hard-codes font_main_plot (size_main). Thread a new
    # 'plotfont' param through the Info_* chain (default font_main_plot, so
    # every other caller is unchanged) and pass font_mini_plot (size_mini,
    # with the skin's own plot linespacing) from the two Home panels only.
    {   # 1) Info_Plot_TextBox: declare the default
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes_Info.xml'),
        'toggle': 'af3_vplot',
        'not_found_ok': True,
        'old': '<param name="use_textbox">Skin.HasSetting(Textboxes.DisableFakeBox)</param>',
        'new': ('<param name="use_textbox">Skin.HasSetting(Textboxes.DisableFakeBox)</param>\n'
                '        <param name="plotfont">font_main_plot</param>  <!-- ABUKARIM: plot font (default) -->'),
        'already_patched_check': '<!-- ABUKARIM: plot font (default) -->',
        'description': 'AF3 - plot font param default (Info_Plot_TextBox)',
    },
    {   # 2) Info_Plot_TextBox: the real-textbox branch uses the param
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes_Info.xml'),
        'toggle': 'af3_vplot',
        'not_found_ok': True,
        'old': '<font>font_main_plot</font>\n                <nested />',
        'new': '<font>$PARAM[plotfont]</font>  <!-- ABUKARIM: plot font (textbox) -->\n                <nested />',
        'already_patched_check': '<!-- ABUKARIM: plot font (textbox) -->',
        'fallback_pattern': r'<font>font_main_plot</font>(\s*<nested />)',
        'fallback_repl': r'<font>$PARAM[plotfont]</font>  <!-- ABUKARIM: plot font (textbox) -->\1',
        'description': 'AF3 - plot textbox uses plotfont param',
    },
    {   # 3) forward plotfont everywhere use_textbox is forwarded (17 sites)
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes_Info.xml'),
        'toggle': 'af3_vplot',
        'not_found_ok': True,
        'old': '',
        'new': '',
        'already_patched_check': '<param name="plotfont">$PARAM[plotfont]</param>',
        'fallback_pattern': r'([ \t]*)(<param name="use_textbox">\$PARAM\[use_textbox\]</param>)',
        'fallback_repl': r'\1\2\n\1<param name="plotfont">$PARAM[plotfont]</param>',
        'count': 0,
        'description': 'AF3 - forward plotfont through the Info_* chain',
    },
    {   # 4) defaults at the chain entry points so nothing forwards an empty font
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes_Info.xml'),
        'toggle': 'af3_vplot',
        'not_found_ok': True,
        'old': '<param name="plotaligny">center</param>',
        'new': ('<param name="plotaligny">center</param>\n'
                '        <param name="plotfont">font_main_plot</param>  <!-- ABUKARIM: plot font (Info_Panel) -->'),
        'already_patched_check': '<!-- ABUKARIM: plot font (Info_Panel) -->',
        'description': 'AF3 - plot font default (Info_Panel)',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes_Info.xml'),
        'toggle': 'af3_vplot',
        'not_found_ok': True,
        'old': '<param name="include_other">true</param>',
        'new': ('<param name="include_other">true</param>\n'
                '        <param name="plotfont">font_main_plot</param>  <!-- ABUKARIM: plot font (Info_Plot) -->'),
        'already_patched_check': '<!-- ABUKARIM: plot font (Info_Plot) -->',
        'description': 'AF3 - plot font default (Info_Plot)',
    },
    {   # 5) Home panels pass the smaller font (anchored on our own vplot lines)
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes_Hubs.xml'),
        'toggle': 'af3_vplot',
        'not_found_ok': True,
        'old': '<param name="use_textbox">true</param>  <!-- ABUKARIM: vertical plot (hub) -->',
        'new': ('<param name="use_textbox">true</param>  <!-- ABUKARIM: vertical plot (hub) -->\n'
                '                    <param name="plotfont">font_mini_plot</param>  <!-- ABUKARIM: plot font (hub) -->'),
        'already_patched_check': '<!-- ABUKARIM: plot font (hub) -->',
        'description': 'AF3 - Home hub plot uses font_mini_plot',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes_Hubs.xml'),
        'toggle': 'af3_vplot',
        'not_found_ok': True,
        'old': '<param name="use_textbox">true</param>  <!-- ABUKARIM: vertical plot (spotlight) -->',
        'new': ('<param name="use_textbox">true</param>  <!-- ABUKARIM: vertical plot (spotlight) -->\n'
                '                <param name="plotfont">font_mini_plot</param>  <!-- ABUKARIM: plot font (spotlight) -->'),
        'already_patched_check': '<!-- ABUKARIM: plot font (spotlight) -->',
        'description': 'AF3 - Home spotlight plot uses font_mini_plot',
    },

    # ── AF3: Vertical Plot — breathing room between the genre/tagline header
    # and the first plot line on Home. The header label is 40px and the plot
    # textbox starts at exactly top=40 (height 80), so the plot's first line
    # sits right under the header, and while scrolling the text clips against
    # it. New params plottop/plotboxh (defaults 40/80 = stock) replace the
    # hard-coded values in Info_Plot_Episode + Info_Plot_Main_Plotline_Content;
    # Home passes top 54 / box 80: the plot moves 14px down (even spacing
    # between the genre line above and the ratings row below); the block
    # height and the ratings row stay put. Every other caller keeps 40/80.
    {   # 1) forward plottop/plotboxh next to every forwarded plotfont
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes_Info.xml'),
        'toggle': 'af3_vplot',
        'not_found_ok': True,
        'old': '',
        'new': '',
        'already_patched_check': '<param name="plottop">$PARAM[plottop]</param>',
        'fallback_pattern': r'([ \t]*)(<param name="plotfont">\$PARAM\[plotfont\]</param>)',
        'fallback_repl': (r'\1\2\n\1<param name="plottop">$PARAM[plottop]</param>'
                          r'\n\1<param name="plotboxh">$PARAM[plotboxh]</param>'),
        'count': 0,
        'description': 'AF3 - forward plot gap params through the Info_* chain',
    },
    {   # 2) header+plot blocks use the params instead of hard-coded 80/40
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes_Info.xml'),
        'toggle': 'af3_vplot',
        'not_found_ok': True,
        'old': '',
        'new': '',
        'already_patched_check': '<!-- ABUKARIM: plot gap -->',
        'fallback_pattern': (r'<param name="height">80</param>(\s*<param name="width">\$PARAM\[width\]</param>\s*)'
                             r'<param name="top">40</param>'),
        'fallback_repl': (r'<param name="height">$PARAM[plotboxh]</param>\1'
                          r'<param name="top">$PARAM[plottop]</param>  <!-- ABUKARIM: plot gap -->'),
        'count': 0,
        'description': 'AF3 - plot textbox top/height from params',
    },
    {   # 3) stock defaults at the chain entry points
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes_Info.xml'),
        'toggle': 'af3_vplot',
        'not_found_ok': True,
        'old': '<param name="plotfont">font_main_plot</param>  <!-- ABUKARIM: plot font (Info_Panel) -->',
        'new': ('<param name="plotfont">font_main_plot</param>  <!-- ABUKARIM: plot font (Info_Panel) -->\n'
                '        <param name="plottop">40</param>\n'
                '        <param name="plotboxh">80</param>  <!-- ABUKARIM: plot gap default (Info_Panel) -->'),
        'already_patched_check': '<!-- ABUKARIM: plot gap default (Info_Panel) -->',
        'description': 'AF3 - plot gap defaults (Info_Panel)',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes_Info.xml'),
        'toggle': 'af3_vplot',
        'not_found_ok': True,
        'old': '<param name="plotfont">font_main_plot</param>  <!-- ABUKARIM: plot font (Info_Plot) -->',
        'new': ('<param name="plotfont">font_main_plot</param>  <!-- ABUKARIM: plot font (Info_Plot) -->\n'
                '        <param name="plottop">40</param>\n'
                '        <param name="plotboxh">80</param>  <!-- ABUKARIM: plot gap default (Info_Plot) -->'),
        'already_patched_check': '<!-- ABUKARIM: plot gap default (Info_Plot) -->',
        'description': 'AF3 - plot gap defaults (Info_Plot)',
    },
    {   # 4) Home panels: gap + two full lines + taller block
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes_Hubs.xml'),
        'toggle': 'af3_vplot',
        'not_found_ok': True,
        'old': '<param name="plotfont">font_mini_plot</param>  <!-- ABUKARIM: plot font (hub) -->',
        'new': ('<param name="plotfont">font_mini_plot</param>  <!-- ABUKARIM: plot font (hub) -->\n'
                '                    <param name="plottop">54</param>\n'
                '                    <param name="plotboxh">80</param>  <!-- ABUKARIM: plot gap (hub) -->'),
        'already_patched_check': '<!-- ABUKARIM: plot gap (hub) -->',
        'description': 'AF3 - Home hub plot gap under the genre line',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes_Hubs.xml'),
        'toggle': 'af3_vplot',
        'not_found_ok': True,
        'old': '<param name="plotfont">font_mini_plot</param>  <!-- ABUKARIM: plot font (spotlight) -->',
        'new': ('<param name="plotfont">font_mini_plot</param>  <!-- ABUKARIM: plot font (spotlight) -->\n'
                '                <param name="plottop">54</param>\n'
                '                <param name="plotboxh">80</param>  <!-- ABUKARIM: plot gap (spotlight) -->'),
        'already_patched_check': '<!-- ABUKARIM: plot gap (spotlight) -->',
        'description': 'AF3 - Home spotlight plot gap under the genre line',
    },

    # ── AF3: Vertical Plot — OSD seek bar / info overlay + library views ──
    # Same treatment as Home (real textbox = vertical autoscroll, font_mini_plot,
    # 54/80 plot gap), using the params the Info_* chain already carries:
    #   * OSD_Progress_Details_Extended (Includes_OSD.xml) — the info block shown
    #     above the seek bar (Custom_1152 / Custom_1153 overlays). It calls
    #     Info_Plot directly, so the params go on that call.
    #   * View_Row_Info (Includes_Views.xml) — the info panel of the library
    #     views opened from the menus / sub-menus.
    #   * View_Combined_Info (Includes_Views_Combined.xml) — the combined views.
    # Every other caller (info dialogs, search, PVR, ...) is unchanged.
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes_OSD.xml'),
        'toggle': 'af3_vplot',
        'not_found_ok': True,
        'old': ('<param name="include_other">false</param>\n'
                '                    <param name="override">true</param>'),
        'new': ('<param name="include_other">false</param>\n'
                '                    <param name="override">true</param>\n'
                '                    <param name="use_textbox">true</param>  <!-- ABUKARIM: vertical plot (osd) -->\n'
                '                    <param name="plotfont">font_mini_plot</param>\n'
                '                    <param name="plottop">54</param>\n'
                '                    <param name="plotboxh">80</param>'),
        'already_patched_check': '<!-- ABUKARIM: vertical plot (osd) -->',
        'fallback_pattern': (r'([ \t]*)(<param name="include_other">false</param>\s*'
                             r'<param name="override">true</param>)'),
        'fallback_repl': (r'\1\2\n\1<param name="use_textbox">true</param>  <!-- ABUKARIM: vertical plot (osd) -->'
                          r'\n\1<param name="plotfont">font_mini_plot</param>'
                          r'\n\1<param name="plottop">54</param>'
                          r'\n\1<param name="plotboxh">80</param>'),
        'description': 'AF3 - OSD seek bar plot scrolls vertically (textbox)',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes_Views.xml'),
        'toggle': 'af3_vplot',
        'not_found_ok': True,
        'old': '<param name="visible_meta">$EXP[View_Row_Info_Details_Expression]</param>',
        'new': ('<param name="visible_meta">$EXP[View_Row_Info_Details_Expression]</param>\n'
                '                <param name="use_textbox">true</param>  <!-- ABUKARIM: vertical plot (views) -->\n'
                '                <param name="plotfont">font_mini_plot</param>\n'
                '                <param name="plottop">54</param>\n'
                '                <param name="plotboxh">80</param>'),
        'already_patched_check': '<!-- ABUKARIM: vertical plot (views) -->',
        'fallback_pattern': r'([ \t]*)(<param name="visible_meta">\$EXP\[View_Row_Info_Details_Expression\]</param>)',
        'fallback_repl': (r'\1\2\n\1<param name="use_textbox">true</param>  <!-- ABUKARIM: vertical plot (views) -->'
                          r'\n\1<param name="plotfont">font_mini_plot</param>'
                          r'\n\1<param name="plottop">54</param>'
                          r'\n\1<param name="plotboxh">80</param>'),
        'description': 'AF3 - library view plot scrolls vertically (textbox)',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes_Views_Combined.xml'),
        'toggle': 'af3_vplot',
        'not_found_ok': True,
        'old': '<param name="include_details">$PARAM[include_details]</param>',
        'new': ('<param name="include_details">$PARAM[include_details]</param>\n'
                '            <param name="use_textbox">true</param>  <!-- ABUKARIM: vertical plot (combined) -->\n'
                '            <param name="plotfont">font_mini_plot</param>\n'
                '            <param name="plottop">54</param>\n'
                '            <param name="plotboxh">80</param>'),
        'already_patched_check': '<!-- ABUKARIM: vertical plot (combined) -->',
        'fallback_pattern': r'([ \t]*)(<param name="include_details">\$PARAM\[include_details\]</param>)',
        'fallback_repl': (r'\1\2\n\1<param name="use_textbox">true</param>  <!-- ABUKARIM: vertical plot (combined) -->'
                          r'\n\1<param name="plotfont">font_mini_plot</param>'
                          r'\n\1<param name="plottop">54</param>'
                          r'\n\1<param name="plotboxh">80</param>'),
        'description': 'AF3 - combined view plot scrolls vertically (textbox)',
    },

    # ── AF3: Highlight Colour — Genre plotline + widget titles (by ABUKARIM TOOLS) ──
    # Paint the Genre plotline (the line above the plot when Plotline = Genre)
    # and every widget header title in the skin's own focus/highlight colour,
    # $VAR[ColorHighlight] — the same var AF3 uses for colordiffuse on its focus
    # textures, so it follows whatever colour the user picked in skin settings.
    {   # 1) Genre plotline — label wrapped in [COLOR=$VAR[ColorHighlight]]
        #    (AF3 uses this exact label syntax itself in Includes_OSD.xml).
        #    Regex fallback also converts the earlier hand-edited red version.
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes_Info.xml'),
        'toggle': 'af3_highlight',
        'not_found_ok': True,
        'old': '<param name="label">$INFO[$PARAM[container]$PARAM[listitem].Genre]</param>',
        'new': ('<param name="label">[COLOR=$VAR[ColorHighlight]]$INFO[$PARAM[container]$PARAM[listitem].Genre][/COLOR]</param>'
                '  <!-- ABUKARIM: genre highlight -->'),
        'already_patched_check': '<!-- ABUKARIM: genre highlight -->',
        'fallback_pattern': (r'<param name="label">\$INFO\[\$PARAM\[container\]\$PARAM\[listitem\]\.Genre[^\n<]*</param>'
                             r'(?:[ \t]*<!-- ABUKARIM: genre in red -->)?'),
        'fallback_repl': ('<param name="label">[COLOR=$VAR[ColorHighlight]]$INFO[$PARAM[container]$PARAM[listitem].Genre][/COLOR]</param>'
                          '  <!-- ABUKARIM: genre highlight -->'),
        'description': 'AF3 - Genre plotline in highlight colour',
    },
    {   # 2) Widget titles — Widget_Label's default-label View_Line
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes_Widgets.xml'),
        'toggle': 'af3_highlight',
        'not_found_ok': True,
        'old': '<param name="label_fallback">31282</param>',
        'new': ('<param name="label_fallback">31282</param>\n'
                '                    <param name="textcolor">$VAR[ColorHighlight]</param>  <!-- ABUKARIM: widget title highlight (label) -->'),
        'already_patched_check': '<!-- ABUKARIM: widget title highlight (label) -->',
        'fallback_pattern': r'([ \t]*)(<param name="label_fallback">31282</param>)',
        'fallback_repl': r'\1\2\n\1<param name="textcolor">$VAR[ColorHighlight]</param>  <!-- ABUKARIM: widget title highlight (label) -->',
        'description': 'AF3 - widget titles in highlight colour',
    },
    {   # 3) Widget titles — Widget_Label's usewidgetlabel View_Line
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes_Widgets.xml'),
        'toggle': 'af3_highlight',
        'not_found_ok': True,
        'old': '<param name="label_fallback">$PARAM[label]</param>',
        'new': ('<param name="label_fallback">$PARAM[label]</param>\n'
                '                    <param name="textcolor">$VAR[ColorHighlight]</param>  <!-- ABUKARIM: widget title highlight (widget) -->'),
        'already_patched_check': '<!-- ABUKARIM: widget title highlight (widget) -->',
        'fallback_pattern': r'([ \t]*)(<param name="label_fallback">\$PARAM\[label\]</param>)',
        'fallback_repl': r'\1\2\n\1<param name="textcolor">$VAR[ColorHighlight]</param>  <!-- ABUKARIM: widget title highlight (widget) -->',
        'description': 'AF3 - widget titles (widget-property label) in highlight colour',
    },

    # ── AF3: auto-trailers support (by ABUKARIM TOOLS, 3.1.16) ──
    # The AF3 auto-trailers (Toggles menu) play a title's trailer WINDOWED; AF3
    # already draws any playing video as the page background. But AF3 also
    # treats any playing media as "the user is watching something": Back on
    # Home/the hubs jumps to full screen (309) and the footer swaps the studio
    # logo for the now-playing panel. Every Player.HasMedia in those three
    # files becomes "real media" = Player.HasMedia AND no trailer property, so
    # a trailer behaves like a moving background. With no trailer playing the
    # property is empty and AF3 behaves exactly as before.
    # Gated by 'feature': only applied while the auto-trailers are turned on.
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes_Hubs.xml'),
        'toggle': 'af3_trailers',
        'feature': 'af3_trailers',
        'not_found_ok': True,
        'old': '',
        'new': '',
        'already_patched_check': 'Window(Home).Property(abk.trailer)',
        'fallback_pattern': r'\bPlayer\.HasMedia\b',
        'fallback_repl': '[Player.HasMedia + String.IsEmpty(Window(Home).Property(abk.trailer))]',
        'count': 0,
        'description': 'AF3 Includes_Hubs.xml - trailers count as background, not playback',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes_Home.xml'),
        'toggle': 'af3_trailers',
        'feature': 'af3_trailers',
        'not_found_ok': True,
        'old': '',
        'new': '',
        'already_patched_check': 'Window(Home).Property(abk.trailer)',
        'fallback_pattern': r'\bPlayer\.HasMedia\b',
        'fallback_repl': '[Player.HasMedia + String.IsEmpty(Window(Home).Property(abk.trailer))]',
        'count': 0,
        'description': 'AF3 Includes_Home.xml - trailers count as background, not playback',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes_Furniture.xml'),
        'toggle': 'af3_trailers',
        'feature': 'af3_trailers',
        'not_found_ok': True,
        'old': '',
        'new': '',
        'already_patched_check': 'Window(Home).Property(abk.trailer)',
        'fallback_pattern': r'\bPlayer\.HasMedia\b',
        'fallback_repl': '[Player.HasMedia + String.IsEmpty(Window(Home).Property(abk.trailer))]',
        'count': 0,
        'description': 'AF3 Includes_Furniture.xml - trailers count as background, not playback',
    },

    # ── AF3: Trailer buttons through the auto-trailer sources (3.2.52) ──
    # The info page's Trailer button, the context menu's Trailer entry and the
    # trailer lists all open AF3's trailer dialog (1123), which PlayMedia()'d
    # TMDbHelper's plugin.video.youtube link - dead without a working YouTube
    # add-on. The dialog now runs trailer_play.py: NewPipe / IMDb in the order
    # set in Toggles, the original link last. Always on (it does not depend on
    # the auto-trailers switch).
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Custom_1123_Dialog_Trailer.xml'),
        'not_found_ok': True,
        'old': '">PlayMedia($ESCINFO[Window(Home).Property(PlayTrailer)],False,1)</onload>',
        'new': ('">RunScript(special://home/addons/plugin.program.abukarimtools/trailer_play.py)</onload>'
                '  <!-- ABUKARIM: trailer button -->'),
        'already_patched_check': '<!-- ABUKARIM: trailer button -->',
        'fallback_pattern': r'">\s*PlayMedia\(\$ESCINFO\[Window\(Home\)\.Property\(PlayTrailer\)\][^<]*\)\s*</onload>',
        'fallback_repl': ('">RunScript(special://home/addons/plugin.program.abukarimtools/trailer_play.py)</onload>'
                          '  <!-- ABUKARIM: trailer button -->'),
        'description': 'AF3 trailer dialog - play through NewPipe/IMDb (auto-trailer sources)',
    },
    {   # the dialog's Repeat button replays the same way
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Dialog_DialogTrailer.xml'),
        'not_found_ok': True,
        'old': '<onclick>PlayMedia($ESCINFO[Window(Home).Property(PlayTrailer)],False,1)</onclick>',
        'new': ('<onclick>RunScript(special://home/addons/plugin.program.abukarimtools/trailer_play.py)</onclick>'
                '<!-- ABUKARIM: trailer button -->'),
        'already_patched_check': '<!-- ABUKARIM: trailer button -->',
        'fallback_pattern': r'<onclick>\s*PlayMedia\(\$ESCINFO\[Window\(Home\)\.Property\(PlayTrailer\)\][^<]*\)\s*</onclick>',
        'fallback_repl': ('<onclick>RunScript(special://home/addons/plugin.program.abukarimtools/trailer_play.py)</onclick>'
                          '<!-- ABUKARIM: trailer button -->'),
        'description': 'AF3 trailer dialog - Repeat plays through NewPipe/IMDb',
    },
    # ── AF3 50.11.x: Trailer button / context-menu Trailer were dead (3.4.15) ──
    # The info page's Trailer button (DialogInfo_VideoButtons_Trailer) and the
    # context menu's Trailer entry both call <include>Action_SelectTrailerSource_OnClick</include>,
    # but AF3 50.11.7 dropped that include from Includes_Actions.xml (it is still
    # in upstream 3.4.0) - an undefined include has no onclick, so pressing
    # Trailer did nothing. This puts it back, opening the trailer dialog (1123)
    # whose onload runs trailer_play.py. Unlike the stock version it never
    # leaves PlayTrailer empty: with no trailer link on the item it passes
    # 'abk://lookup', so the dialog stays open and trailer_play.py finds the
    # trailer by IMDb/TMDb id (the button is shown for TMDb/IMDb-only items too).
    # The sentinel is the include NAME, so if AF3 ships it again natively the
    # entry stands aside.
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes_Actions.xml'),
        'not_found_ok': True,
        'old': '    <include name="Action_PlayTrailer_OnClick">\n',
        'new': _AF3_SELECT_TRAILER_BLOCK + '    <include name="Action_PlayTrailer_OnClick">\n',
        'already_patched_check': 'name="Action_SelectTrailerSource_OnClick"',
        'fallback_pattern': r'([ \t]*)<include name="Action_PlayTrailer_OnClick">',
        'fallback_repl': _AF3_SELECT_TRAILER_BLOCK + r'\g<0>',
        'description': 'AF3 Includes_Actions.xml - restore Action_SelectTrailerSource_OnClick (Trailer button)',
    },

    {   # AF3 auto-trailers (3.1.17): Kodi does not always start the
        # ABUKARIM TOOLS service, so Home also starts the trailer engine by
        # itself (trailers.py) whenever it is not running yet. The condition is
        # evaluated by the skin, so a running engine costs nothing.
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Home.xml'),
        'toggle': 'af3_trailers',
        'feature': 'af3_trailers',
        'not_found_ok': True,
        'old': '<window>\n',
        'new': ('<window>\n'
                '    <onload condition="String.IsEmpty(Window(Home).Property(abukarimtools.trailers.engine))">'
                'RunScript(special://home/addons/plugin.program.abukarimtools/trailers.py,home)</onload>'
                '  <!-- ABUKARIM: trailers engine -->\n'),
        'already_patched_check': '<!-- ABUKARIM: trailers engine -->',
        'fallback_pattern': r'<window>[ \t]*\r?\n',
        'fallback_repl': ('<window>\n'
                          '    <onload condition="String.IsEmpty(Window(Home).Property(abukarimtools.trailers.engine))">'
                          'RunScript(special://home/addons/plugin.program.abukarimtools/trailers.py,home)</onload>'
                          '  <!-- ABUKARIM: trailers engine -->\n'),
        'description': 'AF3 Home.xml - start the trailer engine if it is not running',
    },

    {   # 3.2.14: service guardian. Kodi 22 / Py3.14 sometimes never starts
        # add-on services at boot (ABUKARIM TOOLS, Last Played, DexHub - zero
        # log lines, no error). Home runs guardian.py once per session; it
        # waits 25 s and starts any watched service whose heartbeat is missing.
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Home.xml'),
        'not_found_ok': True,
        'old': '<window>\n',
        'new': ('<window>\n'
                '    <onload condition="String.IsEmpty(Window(Home).Property(abukarimtools.guardian))">'
                'RunScript(special://home/addons/plugin.program.abukarimtools/guardian.py)</onload>'
                '  <!-- ABUKARIM: service guardian -->\n'),
        'already_patched_check': '<!-- ABUKARIM: service guardian -->',
        'fallback_pattern': r'<window>[ \t]*\r?\n',
        'fallback_repl': ('<window>\n'
                          '    <onload condition="String.IsEmpty(Window(Home).Property(abukarimtools.guardian))">'
                          'RunScript(special://home/addons/plugin.program.abukarimtools/guardian.py)</onload>'
                          '  <!-- ABUKARIM: service guardian -->\n'),
        'description': 'AF3 Home.xml - start services Kodi skipped at boot (guardian)',
    },

    {   # AF3 busy-loader waves (3.2.10): Background_BusyLoader shows the
        # resource.images.arctic.waves animation behind everything while
        # DialogBusy is up - i.e. right after a player is picked for a movie.
        # The Toggles entry "AF3: Waves While Loading" flips the skin setting
        # abk.nobusywaves; this always-on patch makes the loader obey it, so
        # the toggle takes effect instantly (no skin reload, no re-patching).
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes_Background.xml'),
        'not_found_ok': True,
        'old': '<visible>Window.IsVisible(DialogBusy.xml)</visible>',
        'new': ('<visible>Window.IsVisible(DialogBusy.xml) + '
                '!Skin.HasSetting(abk.nobusywaves)</visible>'),
        'already_patched_check': '!Skin.HasSetting(abk.nobusywaves)',
        'fallback_pattern': r'<visible>\s*Window\.IsVisible\(DialogBusy\.xml\)\s*</visible>',
        'fallback_repl': ('<visible>Window.IsVisible(DialogBusy.xml) + '
                          '!Skin.HasSetting(abk.nobusywaves)</visible>'),
        'description': 'AF3 busy loader - waves can be switched off (Toggles)',
    },

    # ── AF3: Lucent Look (4.6.8) - colours + glass dialogs ──
    # Phase 1 of the Lucent port to Arctic Fuse 3 (design after the Lucent skin
    # by djdirty60). Always-on and inert until Toggles > "AF3: Lucent Look"
    # sets the skin bool abk.lucent and picks one of the two colour themes:
    #  - two complete colour themes (every AF3 token) in colors/,
    #  - the glass panel textures (same files as the Glass Theme windows) in
    #    media/abk_lucent/,
    #  - Part_Background (the frame of ~30 AF3 dialogs and the Home / Search
    #    side panels): while abk.lucent is set the blur/outline layers hide and
    #    a Lucent glass body (shadow + panel + hairline edge) is drawn instead.
    # With the bool off AF3 looks exactly as unpatched.
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('colors', 'Lucent Glass.xml'),
        'inject_file': True,
        'binary': True,
        'replace': True,
        'not_found_ok': True,
        'inject_source': os.path.join('resources', 'af3_lucent', 'colors', 'Lucent Glass.xml'),
        'description': 'AF3 Lucent Look - colour theme Lucent Glass',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('colors', 'Lucent Glass AMOLED.xml'),
        'inject_file': True,
        'binary': True,
        'replace': True,
        'not_found_ok': True,
        'inject_source': os.path.join('resources', 'af3_lucent', 'colors', 'Lucent Glass AMOLED.xml'),
        'description': 'AF3 Lucent Look - colour theme Lucent Glass AMOLED',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('media', 'abk_lucent', 'panel.png'),
        'inject_file': True,
        'binary': True,
        'replace': True,
        'not_found_ok': True,
        'inject_source': os.path.join('resources', 'lucent', 'media', 'lucent', 'panel.png'),
        'description': 'AF3 Lucent Look - texture panel.png',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('media', 'abk_lucent', 'panel_edge.png'),
        'inject_file': True,
        'binary': True,
        'replace': True,
        'not_found_ok': True,
        'inject_source': os.path.join('resources', 'lucent', 'media', 'lucent', 'panel_edge.png'),
        'description': 'AF3 Lucent Look - texture panel_edge.png',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('media', 'abk_lucent', 'panel_shadow.png'),
        'inject_file': True,
        'binary': True,
        'replace': True,
        'not_found_ok': True,
        'inject_source': os.path.join('resources', 'lucent', 'media', 'lucent', 'panel_shadow.png'),
        'description': 'AF3 Lucent Look - texture panel_shadow.png',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Dialog_Parts.xml'),
        'not_found_ok': True,
        'old': '                <control type="group">\n                    <include content="Part_Background_Blur" condition="$EXP[Exp_DialogTheme_IsAdaptive]">\n                        <param name="shadow">$PARAM[shadow]</param>\n                        <param name="transparency">$PARAM[transparency]</param>\n                    </include>\n                    <include content="Part_Background_Blur_Standard" condition="!$EXP[Exp_DialogTheme_IsAdaptive]">\n                        <param name="shadow">$PARAM[shadow]</param>\n                        <param name="transparency">$PARAM[transparency]</param>\n                    </include>\n                </control>\n                <include condition="$PARAM[include_glass]">Part_Background_Glass</include>',
        'new': '                <control type="group">\n                    <visible>!Skin.HasSetting(abk.lucent)</visible>  <!-- ABUKARIM: Lucent glass dialogs -->\n                    <include content="Part_Background_Blur" condition="$EXP[Exp_DialogTheme_IsAdaptive]">\n                        <param name="shadow">$PARAM[shadow]</param>\n                        <param name="transparency">$PARAM[transparency]</param>\n                    </include>\n                    <include content="Part_Background_Blur_Standard" condition="!$EXP[Exp_DialogTheme_IsAdaptive]">\n                        <param name="shadow">$PARAM[shadow]</param>\n                        <param name="transparency">$PARAM[transparency]</param>\n                    </include>\n                </control>\n                <control type="group">\n                    <visible>Skin.HasSetting(abk.lucent)</visible>\n                    <control type="image">\n                        <left>-40</left>\n                        <top>-40</top>\n                        <right>-40</right>\n                        <bottom>-40</bottom>\n                        <texture border="88">abk_lucent/panel_shadow.png</texture>\n                        <colordiffuse>shadow_hard</colordiffuse>\n                    </control>\n                    <control type="image">\n                        <texture border="48">abk_lucent/panel.png</texture>\n                        <colordiffuse>dialog_overlay</colordiffuse>\n                    </control>\n                    <control type="image">\n                        <texture border="48">abk_lucent/panel_edge.png</texture>\n                        <colordiffuse>overlay_hard</colordiffuse>\n                    </control>\n                </control>\n                <include condition="$PARAM[include_glass]">Part_Background_Glass</include>',
        'already_patched_check': '<!-- ABUKARIM: Lucent glass dialogs -->',
        'description': 'AF3 Lucent Look - glass dialog frame (Part_Background)',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Dialog_Parts.xml'),
        'not_found_ok': True,
        'old': '            <visible>!Skin.String(Background.DialogImage,Onyx)</visible>\n            <texture colordiffuse="dialog_fg_06" border="20">common/dialog.png</texture>',
        'new': '            <visible>!Skin.String(Background.DialogImage,Onyx) + !Skin.HasSetting(abk.lucent)</visible>\n            <texture colordiffuse="dialog_fg_06" border="20">common/dialog.png</texture>',
        'already_patched_check': 'Onyx) + !Skin.HasSetting(abk.lucent)',
        'description': 'AF3 Lucent Look - no AF3 glass sheen over the Lucent body',
    },

    # ── AF3: Lucent Look, phase 2 (4.6.9) - the player ──
    # Thin glass progress bar, glass OSD buttons (white when focused, dark
    # icon), bold time / dimmed duration. Definitions live in our own
    # Includes_ABK_Lucent.xml; the AF3 edits below only insert includes that
    # are gated on Skin.HasSetting(abk.lucent). Kodi uses the FIRST texture /
    # textcolor / font tag of a control, so an include placed before AF3's own
    # tag wins only while the Lucent Look is on. TinyPPI is not touched.
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes_ABK_Lucent.xml'),
        'inject_file': True,
        'binary': True,
        'replace': True,
        'not_found_ok': True,
        'inject_source': os.path.join('resources', 'af3_lucent', 'Includes_ABK_Lucent.xml'),
        'description': 'AF3 Lucent Look - player includes (Includes_ABK_Lucent.xml)',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('media', 'abk_lucent', 'pill6.png'),
        'inject_file': True,
        'binary': True,
        'replace': True,
        'not_found_ok': True,
        'inject_source': os.path.join('resources', 'lucent', 'media', 'lucent', 'pill6.png'),
        'description': 'AF3 Lucent Look - texture pill6.png',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes.xml'),
        'not_found_ok': True,
        'old': '    <include file="Includes_OSD.xml" />',
        'new': '    <include file="Includes_OSD.xml" />\n    <include file="Includes_ABK_Lucent.xml" />  <!-- ABUKARIM: Lucent Look -->',
        'already_patched_check': 'Includes_ABK_Lucent.xml',
        'description': 'AF3 Lucent Look - register Includes_ABK_Lucent.xml',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes_Defaults.xml'),
        'not_found_ok': True,
        'old': '<include>Texture_Circle_Highlight_Focus_V</include>\n            <texturenofocus colordiffuse="$PARAM[back_colordiffuse]">common/circle.png</texturenofocus>',
        'new': '<include condition="Skin.HasSetting(abk.lucent)">ABK_Lucent_OSD_Button_Textures</include>  <!-- ABUKARIM: Lucent OSD buttons -->\n            <include>Texture_Circle_Highlight_Focus_V</include>\n            <texturenofocus colordiffuse="$PARAM[back_colordiffuse]">common/circle.png</texturenofocus>',
        'already_patched_check': '<!-- ABUKARIM: Lucent OSD buttons -->',
        'description': 'AF3 Lucent Look - glass OSD buttons',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes_OSD.xml'),
        'not_found_ok': True,
        'old': '<texture colordiffuse="$VAR[ColorSelected]" flipx="$PARAM[flipx]">$PARAM[icon]</texture>',
        'new': '<include content="ABK_Lucent_IconFocus" condition="Skin.HasSetting(abk.lucent)">  <!-- ABUKARIM: Lucent focused icon -->\n                            <param name="icon">$PARAM[icon]</param>\n                            <param name="flipx">$PARAM[flipx]</param>\n                        </include>\n                        <texture colordiffuse="$VAR[ColorSelected]" flipx="$PARAM[flipx]">$PARAM[icon]</texture>',
        'already_patched_check': '<!-- ABUKARIM: Lucent focused icon -->',
        'description': 'AF3 Lucent Look - dark icon on the focused OSD button',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes_OSD.xml'),
        'not_found_ok': True,
        'old': '<label>$VAR[Label_OSD_Time]</label>\n            <textcolor>panel_fg_100</textcolor>',
        'new': '<label>$VAR[Label_OSD_Time]</label>\n            <include condition="Skin.HasSetting(abk.lucent)">ABK_Lucent_TimeLabel</include>  <!-- ABUKARIM: Lucent time -->\n            <textcolor>panel_fg_100</textcolor>',
        'already_patched_check': '<!-- ABUKARIM: Lucent time -->',
        'description': 'AF3 Lucent Look - bold play time',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes_OSD.xml'),
        'not_found_ok': True,
        'old': '<label>$VAR[Label_OSD_Duration]</label>\n            <textcolor>panel_fg_100</textcolor>',
        'new': '<label>$VAR[Label_OSD_Duration]</label>\n            <include condition="Skin.HasSetting(abk.lucent)">ABK_Lucent_DurationLabel</include>  <!-- ABUKARIM: Lucent duration -->\n            <textcolor>panel_fg_100</textcolor>',
        'already_patched_check': '<!-- ABUKARIM: Lucent duration -->',
        'description': 'AF3 Lucent Look - dimmed duration',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes_OSD.xml'),
        'not_found_ok': True,
        'old': '<include name="OSD_Progress_BarControls">',
        'new': '<include name="OSD_Progress_BarControls">\n        <include condition="Skin.HasSetting(abk.lucent)">ABK_Lucent_Progress</include>  <!-- ABUKARIM: Lucent progress -->',
        'already_patched_check': '<!-- ABUKARIM: Lucent progress -->',
        'description': 'AF3 Lucent Look - thin glass progress bar',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes_OSD.xml'),
        'not_found_ok': True,
        'old': '<!-- Cache Line -->\n        <control type="group">\n            <height>12</height>',
        'new': '<!-- Cache Line -->\n        <control type="group">\n            <visible>!Skin.HasSetting(abk.lucent)</visible>  <!-- ABUKARIM: Lucent hides AF3 cache -->\n            <height>12</height>',
        'already_patched_check': '<!-- ABUKARIM: Lucent hides AF3 cache -->',
        'description': 'AF3 Lucent Look - AF3 cache line off',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes_OSD.xml'),
        'not_found_ok': True,
        'old': '<info>Player.Progress</info>\n            <visible>Player.HasMedia + !Pvr.IsPlayingTv</visible>',
        'new': '<info>Player.Progress</info>\n            <visible>Player.HasMedia + !Pvr.IsPlayingTv + !Skin.HasSetting(abk.lucent)</visible>',
        'already_patched_check': 'Player.HasMedia + !Pvr.IsPlayingTv + !Skin.HasSetting(abk.lucent)',
        'description': 'AF3 Lucent Look - AF3 progress bar off',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes_OSD.xml'),
        'not_found_ok': True,
        'old': '<info>PVR.EpgEventProgress</info>\n            <visible>Pvr.IsPlayingTv</visible>',
        'new': '<info>PVR.EpgEventProgress</info>\n            <visible>Pvr.IsPlayingTv + !Skin.HasSetting(abk.lucent)</visible>',
        'already_patched_check': '<visible>Pvr.IsPlayingTv + !Skin.HasSetting(abk.lucent)</visible>',
        'description': 'AF3 Lucent Look - AF3 live TV bar off',
    },

    # ── AF3: Lucent Look, phase 3 (4.6.10) - the info page ──
    # The action buttons of the video info page (Play, Trailer, Trakt, ...,
    # Options - grouplists 9000 in Includes_DialogInfo.xml) and the plot
    # dialog tabs all come from Button_Underline_Switcher. While abk.lucent is
    # set they become Lucent pills (first tag wins, see phase 2) and the two
    # info-page rows use a tighter gap. Definitions in Includes_ABK_Lucent.xml.
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('media', 'abk_lucent', 'pill60.png'),
        'inject_file': True,
        'binary': True,
        'replace': True,
        'not_found_ok': True,
        'inject_source': os.path.join('resources', 'lucent', 'media', 'lucent', 'pill60.png'),
        'description': 'AF3 Lucent Look - texture pill60.png',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes_Buttons.xml'),
        'not_found_ok': True,
        'old': '            <control type="$PARAM[control]" id="$PARAM[id]">\n                <nested />\n                <width>auto</width>',
        'new': '            <control type="$PARAM[control]" id="$PARAM[id]">\n                <nested />\n                <include condition="Skin.HasSetting(abk.lucent)">ABK_Lucent_PillButton</include>  <!-- ABUKARIM: Lucent pill buttons -->\n                <width>auto</width>',
        'already_patched_check': '<!-- ABUKARIM: Lucent pill buttons -->',
        'description': 'AF3 Lucent Look - pill action buttons (info page, plot tabs)',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes_DialogInfo.xml'),
        'not_found_ok': True,
        'old': '<itemgap>40</itemgap>\n                    <ondown>90001</ondown>',
        'new': '<include condition="Skin.HasSetting(abk.lucent)">ABK_Lucent_PillGap</include>  <!-- ABUKARIM: Lucent pill gap 90001 -->\n                    <itemgap>40</itemgap>\n                    <ondown>90001</ondown>',
        'already_patched_check': '<!-- ABUKARIM: Lucent pill gap 90001 -->',
        'description': 'AF3 Lucent Look - tighter button row (info)',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes_DialogInfo.xml'),
        'not_found_ok': True,
        'old': '<itemgap>40</itemgap>\n                    <ondown>5000</ondown>',
        'new': '<include condition="Skin.HasSetting(abk.lucent)">ABK_Lucent_PillGap</include>  <!-- ABUKARIM: Lucent pill gap 5000 -->\n                    <itemgap>40</itemgap>\n                    <ondown>5000</ondown>',
        'already_patched_check': '<!-- ABUKARIM: Lucent pill gap 5000 -->',
        'description': 'AF3 Lucent Look - tighter button row (info, alt layout)',
    },

    # ── AF3: Lucent Look, phase 4 (4.6.11) - Lucent focus ──
    # Lucent focuses with a solid white highlight and dark text. AF3's own
    # default is the same (ColorHighlight ffffffff, ColorSelected ff272727),
    # so every AF3 view already supports it; while abk.lucent is set the four
    # focus variables take the Lucent values first, over the user's chosen
    # focus colour / "revert selected text". Variables are live: no reload.
    # 4.6.12: optional - skin bool abk.lucent.ownfocus (Toggles > AF3: Lucent
    # Look > "Focus colour") keeps the user's own focus colour. The regex
    # fallback upgrades a skin patched by 4.6.11 in place.
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes_Colors.xml'),
        'not_found_ok': True,
        'old': '<variable name="ColorHighlight">\n        <value condition="!',
        'new': '<variable name="ColorHighlight">\n        <value condition="Skin.HasSetting(abk.lucent) + !Skin.HasSetting(abk.lucent.ownfocus)">ffffffff</value>  <!-- ABUKARIM: Lucent focus -->\n        <value condition="!',
        'already_patched_check': '<variable name="ColorHighlight">\n        <value condition="Skin.HasSetting(abk.lucent) + !Skin.HasSetting(abk.lucent.ownfocus)">ffffffff</value>  <!-- ABUKARIM: Lucent focus -->',
        'fallback_pattern': '(<variable name="ColorHighlight">\\n)        <value condition="Skin\\.HasSetting\\(abk\\.lucent\\)">[0-9a-fA-F]{8}</value>  <!-- ABUKARIM: Lucent focus -->\\n',
        'fallback_repl': '\\g<1>        <value condition="Skin.HasSetting(abk.lucent) + !Skin.HasSetting(abk.lucent.ownfocus)">ffffffff</value>  <!-- ABUKARIM: Lucent focus -->\n',
        'description': 'AF3 Lucent Look - Lucent focus (ColorHighlight)',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes_Colors.xml'),
        'not_found_ok': True,
        'old': '<variable name="ColorSelected_30">\n        <value condition="!',
        'new': '<variable name="ColorSelected_30">\n        <value condition="Skin.HasSetting(abk.lucent) + !Skin.HasSetting(abk.lucent.ownfocus)">4d0b1119</value>  <!-- ABUKARIM: Lucent focus -->\n        <value condition="!',
        'already_patched_check': '<variable name="ColorSelected_30">\n        <value condition="Skin.HasSetting(abk.lucent) + !Skin.HasSetting(abk.lucent.ownfocus)">4d0b1119</value>  <!-- ABUKARIM: Lucent focus -->',
        'fallback_pattern': '(<variable name="ColorSelected_30">\\n)        <value condition="Skin\\.HasSetting\\(abk\\.lucent\\)">[0-9a-fA-F]{8}</value>  <!-- ABUKARIM: Lucent focus -->\\n',
        'fallback_repl': '\\g<1>        <value condition="Skin.HasSetting(abk.lucent) + !Skin.HasSetting(abk.lucent.ownfocus)">4d0b1119</value>  <!-- ABUKARIM: Lucent focus -->\n',
        'description': 'AF3 Lucent Look - Lucent focus (ColorSelected_30)',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes_Colors.xml'),
        'not_found_ok': True,
        'old': '<variable name="ColorSelected">\n        <value condition="!',
        'new': '<variable name="ColorSelected">\n        <value condition="Skin.HasSetting(abk.lucent) + !Skin.HasSetting(abk.lucent.ownfocus)">ff0b1119</value>  <!-- ABUKARIM: Lucent focus -->\n        <value condition="!',
        'already_patched_check': '<variable name="ColorSelected">\n        <value condition="Skin.HasSetting(abk.lucent) + !Skin.HasSetting(abk.lucent.ownfocus)">ff0b1119</value>  <!-- ABUKARIM: Lucent focus -->',
        'fallback_pattern': '(<variable name="ColorSelected">\\n)        <value condition="Skin\\.HasSetting\\(abk\\.lucent\\)">[0-9a-fA-F]{8}</value>  <!-- ABUKARIM: Lucent focus -->\\n',
        'fallback_repl': '\\g<1>        <value condition="Skin.HasSetting(abk.lucent) + !Skin.HasSetting(abk.lucent.ownfocus)">ff0b1119</value>  <!-- ABUKARIM: Lucent focus -->\n',
        'description': 'AF3 Lucent Look - Lucent focus (ColorSelected)',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes_Colors.xml'),
        'not_found_ok': True,
        'old': '<variable name="ColorSelectedInverted">\n        <value condition="!',
        'new': '<variable name="ColorSelectedInverted">\n        <value condition="Skin.HasSetting(abk.lucent) + !Skin.HasSetting(abk.lucent.ownfocus)">ffffffff</value>  <!-- ABUKARIM: Lucent focus -->\n        <value condition="!',
        'already_patched_check': '<variable name="ColorSelectedInverted">\n        <value condition="Skin.HasSetting(abk.lucent) + !Skin.HasSetting(abk.lucent.ownfocus)">ffffffff</value>  <!-- ABUKARIM: Lucent focus -->',
        'fallback_pattern': '(<variable name="ColorSelectedInverted">\\n)        <value condition="Skin\\.HasSetting\\(abk\\.lucent\\)">[0-9a-fA-F]{8}</value>  <!-- ABUKARIM: Lucent focus -->\\n',
        'fallback_repl': '\\g<1>        <value condition="Skin.HasSetting(abk.lucent) + !Skin.HasSetting(abk.lucent.ownfocus)">ffffffff</value>  <!-- ABUKARIM: Lucent focus -->\n',
        'description': 'AF3 Lucent Look - Lucent focus (ColorSelectedInverted)',
    },

    # ── AF3: Lucent Look, phase 5 (4.6.14) - player icons ──
    # Thin rounded line icons in the Lucent style for the player buttons
    # (our own drawings, tools/gen_af3_lucent_icons.py - Lucent's PNGs are
    # not copied). Installed in media/abk_lucent/icons/. Gated on abk.lucent:
    #  - Image_OSD_PausePlay / PlayPause / SkipPrev / SkipNext take a Lucent
    #    value first;
    #  - the buttons with a fixed icon now read $VAR[ABK_LucentIcon_<key>],
    #    defined at the top of Includes_Images.xml with AF3's own icon as the
    #    fallback value, so nothing changes with the look off. The block goes
    #    in first (regex after <includes>) so the variables always exist.
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('media', 'abk_lucent', 'icons', 'play.png'),
        'inject_file': True,
        'binary': True,
        'replace': True,
        'not_found_ok': True,
        'inject_source': os.path.join('resources', 'af3_lucent', 'icons', 'play.png'),
        'description': 'AF3 Lucent Look - icon play',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('media', 'abk_lucent', 'icons', 'pause.png'),
        'inject_file': True,
        'binary': True,
        'replace': True,
        'not_found_ok': True,
        'inject_source': os.path.join('resources', 'af3_lucent', 'icons', 'pause.png'),
        'description': 'AF3 Lucent Look - icon pause',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('media', 'abk_lucent', 'icons', 'forward.png'),
        'inject_file': True,
        'binary': True,
        'replace': True,
        'not_found_ok': True,
        'inject_source': os.path.join('resources', 'af3_lucent', 'icons', 'forward.png'),
        'description': 'AF3 Lucent Look - icon forward',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('media', 'abk_lucent', 'icons', 'rewind.png'),
        'inject_file': True,
        'binary': True,
        'replace': True,
        'not_found_ok': True,
        'inject_source': os.path.join('resources', 'af3_lucent', 'icons', 'rewind.png'),
        'description': 'AF3 Lucent Look - icon rewind',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('media', 'abk_lucent', 'icons', 'prev.png'),
        'inject_file': True,
        'binary': True,
        'replace': True,
        'not_found_ok': True,
        'inject_source': os.path.join('resources', 'af3_lucent', 'icons', 'prev.png'),
        'description': 'AF3 Lucent Look - icon prev',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('media', 'abk_lucent', 'icons', 'next.png'),
        'inject_file': True,
        'binary': True,
        'replace': True,
        'not_found_ok': True,
        'inject_source': os.path.join('resources', 'af3_lucent', 'icons', 'next.png'),
        'description': 'AF3 Lucent Look - icon next',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('media', 'abk_lucent', 'icons', 'stop.png'),
        'inject_file': True,
        'binary': True,
        'replace': True,
        'not_found_ok': True,
        'inject_source': os.path.join('resources', 'af3_lucent', 'icons', 'stop.png'),
        'description': 'AF3 Lucent Look - icon stop',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('media', 'abk_lucent', 'icons', 'info.png'),
        'inject_file': True,
        'binary': True,
        'replace': True,
        'not_found_ok': True,
        'inject_source': os.path.join('resources', 'af3_lucent', 'icons', 'info.png'),
        'description': 'AF3 Lucent Look - icon info',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('media', 'abk_lucent', 'icons', 'audio.png'),
        'inject_file': True,
        'binary': True,
        'replace': True,
        'not_found_ok': True,
        'inject_source': os.path.join('resources', 'af3_lucent', 'icons', 'audio.png'),
        'description': 'AF3 Lucent Look - icon audio',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('media', 'abk_lucent', 'icons', 'subtitles.png'),
        'inject_file': True,
        'binary': True,
        'replace': True,
        'not_found_ok': True,
        'inject_source': os.path.join('resources', 'af3_lucent', 'icons', 'subtitles.png'),
        'description': 'AF3 Lucent Look - icon subtitles',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('media', 'abk_lucent', 'icons', 'video.png'),
        'inject_file': True,
        'binary': True,
        'replace': True,
        'not_found_ok': True,
        'inject_source': os.path.join('resources', 'af3_lucent', 'icons', 'video.png'),
        'description': 'AF3 Lucent Look - icon video',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('media', 'abk_lucent', 'icons', 'list.png'),
        'inject_file': True,
        'binary': True,
        'replace': True,
        'not_found_ok': True,
        'inject_source': os.path.join('resources', 'af3_lucent', 'icons', 'list.png'),
        'description': 'AF3 Lucent Look - icon list',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('media', 'abk_lucent', 'icons', 'record.png'),
        'inject_file': True,
        'binary': True,
        'replace': True,
        'not_found_ok': True,
        'inject_source': os.path.join('resources', 'af3_lucent', 'icons', 'record.png'),
        'description': 'AF3 Lucent Look - icon record',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('media', 'abk_lucent', 'icons', 'subcycler.png'),
        'inject_file': True,
        'binary': True,
        'replace': True,
        'not_found_ok': True,
        'inject_source': os.path.join('resources', 'af3_lucent', 'icons', 'subcycler.png'),
        'description': 'AF3 Lucent Look - icon subcycler',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('media', 'abk_lucent', 'icons', 'dexsync.png'),
        'inject_file': True,
        'binary': True,
        'replace': True,
        'not_found_ok': True,
        'inject_source': os.path.join('resources', 'af3_lucent', 'icons', 'dexsync.png'),
        'description': 'AF3 Lucent Look - icon dexsync',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('media', 'abk_lucent', 'icons', 'substyle.png'),
        'inject_file': True,
        'binary': True,
        'replace': True,
        'not_found_ok': True,
        'inject_source': os.path.join('resources', 'af3_lucent', 'icons', 'substyle.png'),
        'description': 'AF3 Lucent Look - icon substyle',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('media', 'abk_lucent', 'icons', 'ppi.png'),
        'inject_file': True,
        'binary': True,
        'replace': True,
        'not_found_ok': True,
        'inject_source': os.path.join('resources', 'af3_lucent', 'icons', 'ppi.png'),
        'description': 'AF3 Lucent Look - icon ppi',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes_Images.xml'),
        'not_found_ok': True,
        'old': '',
        'new': '',
        'already_patched_check': '<!-- ABUKARIM: Lucent icons',
        'fallback_pattern': '(<includes>[ \\t]*\\r?\\n)',
        'fallback_repl': '\\g<1>    <!-- ABUKARIM: Lucent icons (AB Tools "AF3: Lucent Look"; AF3 icon when off) -->\n    <variable name="ABK_LucentIcon_list">\n        <value condition="Skin.HasSetting(abk.lucent)">abk_lucent/icons/list.png</value>\n        <value>special://skin/extras/icons/list.png</value>\n    </variable>\n    <variable name="ABK_LucentIcon_record">\n        <value condition="Skin.HasSetting(abk.lucent)">abk_lucent/icons/record.png</value>\n        <value>special://skin/extras/icons/record-vinyl.png</value>\n    </variable>\n    <variable name="ABK_LucentIcon_stop">\n        <value condition="Skin.HasSetting(abk.lucent)">abk_lucent/icons/stop.png</value>\n        <value>special://skin/extras/icons/stop.png</value>\n    </variable>\n    <variable name="ABK_LucentIcon_info">\n        <value condition="Skin.HasSetting(abk.lucent)">abk_lucent/icons/info.png</value>\n        <value>special://skin/extras/icons/info2.png</value>\n    </variable>\n    <variable name="ABK_LucentIcon_audio">\n        <value condition="Skin.HasSetting(abk.lucent)">abk_lucent/icons/audio.png</value>\n        <value>special://skin/extras/icons/volume.png</value>\n    </variable>\n    <variable name="ABK_LucentIcon_subtitles">\n        <value condition="Skin.HasSetting(abk.lucent)">abk_lucent/icons/subtitles.png</value>\n        <value>special://skin/extras/icons/quote.png</value>\n    </variable>\n    <variable name="ABK_LucentIcon_video">\n        <value condition="Skin.HasSetting(abk.lucent)">abk_lucent/icons/video.png</value>\n        <value>special://skin/extras/icons/video.png</value>\n    </variable>\n\n',
        'description': 'AF3 Lucent Look - icon variables (Includes_Images.xml)',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes_Images.xml'),
        'not_found_ok': True,
        'old': '<variable name="Image_OSD_PausePlay">\n        <value condition="Player.Playing">',
        'new': '<variable name="Image_OSD_PausePlay">\n        <value condition="Skin.HasSetting(abk.lucent) + Player.Playing">abk_lucent/icons/pause.png</value>  <!-- ABUKARIM: Lucent icon -->\n        <value condition="Skin.HasSetting(abk.lucent)">abk_lucent/icons/play.png</value>  <!-- ABUKARIM: Lucent icon -->\n        <value condition="Player.Playing">',
        'already_patched_check': '<variable name="Image_OSD_PausePlay">\n        <value condition="Skin.HasSetting(abk.lucent) + Player.Playing">',
        'description': 'AF3 Lucent Look - play / pause icon (OSD open)',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes_Images.xml'),
        'not_found_ok': True,
        'old': '$VAR[Image_OSD_PausePlay]</value>\n        <value condition="Player.Paused">special://skin/extras/icons/pause.png</value>',
        'new': '$VAR[Image_OSD_PausePlay]</value>\n        <value condition="Skin.HasSetting(abk.lucent) + Player.Paused">abk_lucent/icons/pause.png</value>  <!-- ABUKARIM: Lucent icon -->\n        <value condition="Skin.HasSetting(abk.lucent) + Player.Forwarding">abk_lucent/icons/forward.png</value>  <!-- ABUKARIM: Lucent icon -->\n        <value condition="Skin.HasSetting(abk.lucent) + Player.Rewinding">abk_lucent/icons/rewind.png</value>  <!-- ABUKARIM: Lucent icon -->\n        <value condition="Skin.HasSetting(abk.lucent)">abk_lucent/icons/play.png</value>  <!-- ABUKARIM: Lucent icon -->\n        <value condition="Player.Paused">special://skin/extras/icons/pause.png</value>',
        'already_patched_check': '<value condition="Skin.HasSetting(abk.lucent) + Player.Paused">abk_lucent/icons/pause.png',
        'description': 'AF3 Lucent Look - play state icon (seek bar)',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes_Images.xml'),
        'not_found_ok': True,
        'old': '<variable name="Image_OSD_SkipPrev">\n        <value condition="!String.IsEmpty(Player.Chapter)',
        'new': '<variable name="Image_OSD_SkipPrev">\n        <value condition="Skin.HasSetting(abk.lucent)">abk_lucent/icons/prev.png</value>  <!-- ABUKARIM: Lucent icon -->\n        <value condition="!String.IsEmpty(Player.Chapter)',
        'already_patched_check': '<variable name="Image_OSD_SkipPrev">\n        <value condition="Skin.HasSetting(abk.lucent)">',
        'description': 'AF3 Lucent Look - prev icon',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes_Images.xml'),
        'not_found_ok': True,
        'old': '<variable name="Image_OSD_SkipNext">\n        <value condition="!String.IsEmpty(Player.Chapter)',
        'new': '<variable name="Image_OSD_SkipNext">\n        <value condition="Skin.HasSetting(abk.lucent)">abk_lucent/icons/next.png</value>  <!-- ABUKARIM: Lucent icon -->\n        <value condition="!String.IsEmpty(Player.Chapter)',
        'already_patched_check': '<variable name="Image_OSD_SkipNext">\n        <value condition="Skin.HasSetting(abk.lucent)">',
        'description': 'AF3 Lucent Look - next icon',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'VideoOSD.xml'),
        'not_found_ok': True,
        'old': '<param name="icon">special://skin/extras/icons/list.png</param>',
        'new': '<param name="icon">$VAR[ABK_LucentIcon_list]</param>',
        'already_patched_check': '$VAR[ABK_LucentIcon_list]',
        'description': 'AF3 Lucent Look - OSD button icon list',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'VideoOSD.xml'),
        'not_found_ok': True,
        'old': '<param name="icon">special://skin/extras/icons/record-vinyl.png</param>',
        'new': '<param name="icon">$VAR[ABK_LucentIcon_record]</param>',
        'already_patched_check': '$VAR[ABK_LucentIcon_record]',
        'description': 'AF3 Lucent Look - OSD button icon record',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'VideoOSD.xml'),
        'not_found_ok': True,
        'old': '<param name="icon">special://skin/extras/icons/stop.png</param>',
        'new': '<param name="icon">$VAR[ABK_LucentIcon_stop]</param>',
        'already_patched_check': '$VAR[ABK_LucentIcon_stop]',
        'description': 'AF3 Lucent Look - OSD button icon stop',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'VideoOSD.xml'),
        'not_found_ok': True,
        'old': '<param name="icon">special://skin/extras/icons/info2.png</param>',
        'new': '<param name="icon">$VAR[ABK_LucentIcon_info]</param>',
        'already_patched_check': '$VAR[ABK_LucentIcon_info]',
        'description': 'AF3 Lucent Look - OSD button icon info',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'VideoOSD.xml'),
        'not_found_ok': True,
        'old': '<param name="icon">special://skin/extras/icons/volume.png</param>',
        'new': '<param name="icon">$VAR[ABK_LucentIcon_audio]</param>',
        'already_patched_check': '$VAR[ABK_LucentIcon_audio]',
        'description': 'AF3 Lucent Look - OSD button icon audio',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'VideoOSD.xml'),
        'not_found_ok': True,
        'old': '<param name="icon">special://skin/extras/icons/quote.png</param>',
        'new': '<param name="icon">$VAR[ABK_LucentIcon_subtitles]</param>',
        'already_patched_check': '$VAR[ABK_LucentIcon_subtitles]',
        'description': 'AF3 Lucent Look - OSD button icon subtitles',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'VideoOSD.xml'),
        'not_found_ok': True,
        'old': '<param name="icon">special://skin/extras/icons/video.png</param>',
        'new': '<param name="icon">$VAR[ABK_LucentIcon_video]</param>',
        'already_patched_check': '$VAR[ABK_LucentIcon_video]',
        'description': 'AF3 Lucent Look - OSD button icon video',
    },

    # 4.6.22 (screen recording 2026-10-31 08:50): one icon set on the whole
    # OSD row. The AB Tools buttons (Subtitle Cycler, DexSubtitles sync,
    # Subtitle Look) and AF3's PPI button get Lucent line icons too, and AF3's
    # stream popups (1145-1148) - which redraw the focused button over the
    # bar - use the same Lucent icons instead of AF3's speaker / quote / film,
    # so a button keeps its icon (white on glass, dark on the white focus).
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes_Images.xml'),
        'not_found_ok': True,
        'old': '    <!-- ABUKARIM: Lucent icons (AB Tools "AF3: Lucent Look"; AF3 icon when off) -->\n',
        'new': '    <!-- ABUKARIM: Lucent icons (AB Tools "AF3: Lucent Look"; AF3 icon when off) -->\n    <variable name="ABK_LucentIcon_subcycler">\n        <value condition="Skin.HasSetting(abk.lucent)">abk_lucent/icons/subcycler.png</value>\n        <value>special://skin/extras/icons/subcycler.png</value>\n    </variable>\n    <variable name="ABK_LucentIcon_dexsync">\n        <value condition="Skin.HasSetting(abk.lucent)">abk_lucent/icons/dexsync.png</value>\n        <value>special://skin/extras/icons/dexsync.png</value>\n    </variable>\n    <variable name="ABK_LucentIcon_substyle">\n        <value condition="Skin.HasSetting(abk.lucent)">abk_lucent/icons/substyle.png</value>\n        <value>special://skin/extras/icons/substyle.png</value>\n    </variable>\n    <variable name="ABK_LucentIcon_ppi">\n        <value condition="Skin.HasSetting(abk.lucent)">abk_lucent/icons/ppi.png</value>\n        <value>special://skin/extras/icons/ppi.png</value>\n    </variable>\n',
        'already_patched_check': '<variable name="ABK_LucentIcon_ppi">',
        'description': 'AF3 Lucent Look - icon variables for the AB Tools / PPI buttons',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'VideoOSD.xml'),
        'not_found_ok': True,
        'old': '<param name="icon">special://skin/extras/icons/dexsync.png</param>',
        'new': '<param name="icon">$VAR[ABK_LucentIcon_dexsync]</param>',
        'already_patched_check': '<param name="icon">$VAR[ABK_LucentIcon_dexsync]</param>',
        'description': 'AF3 Lucent Look - OSD button icon dexsync',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'VideoOSD.xml'),
        'not_found_ok': True,
        'old': '<param name="icon">special://skin/extras/icons/subcycler.png</param>',
        'new': '<param name="icon">$VAR[ABK_LucentIcon_subcycler]</param>',
        'already_patched_check': '<param name="icon">$VAR[ABK_LucentIcon_subcycler]</param>',
        'description': 'AF3 Lucent Look - OSD button icon subcycler',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'VideoOSD.xml'),
        'not_found_ok': True,
        'old': '<param name="icon">special://skin/extras/icons/substyle.png</param>',
        'new': '<param name="icon">$VAR[ABK_LucentIcon_substyle]</param>',
        'already_patched_check': '<param name="icon">$VAR[ABK_LucentIcon_substyle]</param>',
        'description': 'AF3 Lucent Look - OSD button icon substyle',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes_u3k.xml'),
        'not_found_ok': True,
        'old': '<param name="icon">special://skin/extras/icons/ppi.png</param>',
        'new': '<param name="icon">$VAR[ABK_LucentIcon_ppi]</param>',
        'already_patched_check': '$VAR[ABK_LucentIcon_ppi]',
        'description': 'AF3 Lucent Look - OSD button icon ppi',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Custom_1145_OSD_InfoPanel.xml'),
        'not_found_ok': True,
        'old': '\n                <param name="icon">special://skin/extras/icons/info2.png</param>',
        'new': '\n                <param name="icon">$VAR[ABK_LucentIcon_info]</param>',
        'already_patched_check': '\n                <param name="icon">$VAR[ABK_LucentIcon_info]</param>',
        'description': 'AF3 Lucent Look - popup icon info (button)',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Custom_1146_OSD_AudioStreams.xml'),
        'not_found_ok': True,
        'old': '\n                    <param name="icon">special://skin/extras/icons/volume.png</param>',
        'new': '\n                    <param name="icon">$VAR[ABK_LucentIcon_audio]</param>',
        'already_patched_check': '\n                    <param name="icon">$VAR[ABK_LucentIcon_audio]</param>',
        'description': 'AF3 Lucent Look - popup icon audio (list header)',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Custom_1146_OSD_AudioStreams.xml'),
        'not_found_ok': True,
        'old': '\n                <param name="icon">special://skin/extras/icons/volume.png</param>',
        'new': '\n                <param name="icon">$VAR[ABK_LucentIcon_audio]</param>',
        'already_patched_check': '\n                <param name="icon">$VAR[ABK_LucentIcon_audio]</param>',
        'description': 'AF3 Lucent Look - popup icon audio (button)',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Custom_1147_OSD_SubtitleStreams.xml'),
        'not_found_ok': True,
        'old': '\n                    <param name="icon">special://skin/extras/icons/quote.png</param>',
        'new': '\n                    <param name="icon">$VAR[ABK_LucentIcon_subtitles]</param>',
        'already_patched_check': '\n                    <param name="icon">$VAR[ABK_LucentIcon_subtitles]</param>',
        'description': 'AF3 Lucent Look - popup icon subtitles (list header)',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Custom_1147_OSD_SubtitleStreams.xml'),
        'not_found_ok': True,
        'old': '\n                <param name="icon">special://skin/extras/icons/quote.png</param>',
        'new': '\n                <param name="icon">$VAR[ABK_LucentIcon_subtitles]</param>',
        'already_patched_check': '\n                <param name="icon">$VAR[ABK_LucentIcon_subtitles]</param>',
        'description': 'AF3 Lucent Look - popup icon subtitles (button)',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Custom_1148_OSD_VideoStreams.xml'),
        'not_found_ok': True,
        'old': '\n                    <param name="icon">special://skin/extras/icons/video.png</param>',
        'new': '\n                    <param name="icon">$VAR[ABK_LucentIcon_video]</param>',
        'already_patched_check': '\n                    <param name="icon">$VAR[ABK_LucentIcon_video]</param>',
        'description': 'AF3 Lucent Look - popup icon video (list header)',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Custom_1148_OSD_VideoStreams.xml'),
        'not_found_ok': True,
        'old': '\n                <param name="icon">special://skin/extras/icons/video.png</param>',
        'new': '\n                <param name="icon">$VAR[ABK_LucentIcon_video]</param>',
        'already_patched_check': '\n                <param name="icon">$VAR[ABK_LucentIcon_video]</param>',
        'description': 'AF3 Lucent Look - popup icon video (button)',
    },

    # ── AF3: Lucent Look (4.6.14) - subtitle list from the OSD button ──
    # After Lucent 1.31.39: the subtitle button opens one list (on / off,
    # the video's subtitles in your languages, other languages, online
    # search, subtitle look) - resources/lib/sub_list.py. Only while the
    # Lucent Look is on; otherwise Kodi's subtitle settings as before.
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'VideoOSD.xml'),
        'not_found_ok': True,
        'old': '                            <onclick>CancelAlarm(osd_timeout,true)</onclick>\n                            <onclick>ActivateWindow(osdsubtitlesettings)</onclick>',
        'new': '                            <onclick>CancelAlarm(osd_timeout,true)</onclick>\n                            <onclick condition="Skin.HasSetting(abk.lucent)">RunPlugin(plugin://plugin.program.abukarimtools/?mode=subtitle_list)</onclick>  <!-- ABUKARIM: Lucent subtitle list -->\n                            <onclick condition="!Skin.HasSetting(abk.lucent)">ActivateWindow(osdsubtitlesettings)</onclick>',
        'already_patched_check': '<!-- ABUKARIM: Lucent subtitle list -->',
        'description': 'AF3 Lucent Look - subtitle button opens the subtitle list',
    },

    # ── AF3: Plot on the Right (4.6.15) ──
    # Toggles > "AF3: Plot on the Right" sets the skin bool abk.plotright.
    # Always-on, inert with the bool off. On the Home page (Spotlight and
    # the combined hub info) the plot leaves the left column - Info_Plot is
    # one item of a vertical grouplist, so the ratings / meta lines move up
    # and no gap is left - and shows complete in a glass box on the empty
    # right side (right-anchored, so it fits every AF3 aspect ratio):
    # episode heading, plot right-aligned in Arabic, auto-scroll when long.
    # Font: font_mini_plot for now (one place to change: FONT below).
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes_Hubs.xml'),
        'not_found_ok': True,
        'old': '<include name="Hub_Spotlight_Info">\n        <control type="group">',
        'new': '<include name="Hub_Spotlight_Info">\n        <!-- ABUKARIM: plot on the right -->\n        <control type="group">\n            <visible>Skin.HasSetting(abk.plotright) + !$EXP[Exp_InfoDialogs] + $EXP[Hub_Spotlight_Visible_Expression] + String.IsEmpty(Window(Home).Property(Background.ShowOverlay)) + !String.IsEmpty(Container(301).ListItem.Plot)</visible>\n            <animation effect="slide" end="0" start="0,-200" time="400" tween="cubic" easing="out" reversible="false" condition="!Control.HasFocus(300)">Visible</animation>\n            <animation effect="slide" start="0" end="0,-200" time="400" tween="cubic" easing="out" reversible="false">Hidden</animation>\n            <right>120</right>\n            <width>700</width>\n            <top>164</top>\n            <height>283</height>\n            <!-- ABUKARIM: plot box 4.6.21 (Spotlight): glass inside the page margin, centred on the info column -->\n            <!-- probes: invisible copies of the plot, one per line count (line = 35 px);\n                 Container(id).NumPages = 1 when the plot fits that height -->\n            <control type="textbox" id="9341">\n                <width>700</width>\n                <height>38</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container(301).ListItem.Plot]</label>\n            </control>\n            <control type="textbox" id="9342">\n                <width>700</width>\n                <height>73</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container(301).ListItem.Plot]</label>\n            </control>\n            <control type="textbox" id="9343">\n                <width>700</width>\n                <height>108</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container(301).ListItem.Plot]</label>\n            </control>\n            <control type="textbox" id="9344">\n                <width>700</width>\n                <height>143</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container(301).ListItem.Plot]</label>\n            </control>\n            <control type="textbox" id="9345">\n                <width>700</width>\n                <height>178</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container(301).ListItem.Plot]</label>\n            </control>\n            <control type="textbox" id="9346">\n                <width>700</width>\n                <height>213</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container(301).ListItem.Plot]</label>\n            </control>\n            <control type="textbox" id="9347">\n                <width>700</width>\n                <height>248</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container(301).ListItem.Plot]</label>\n            </control>\n            <!-- the box: the smallest height that holds the plot, centred on the info column -->\n            <control type="group">\n                <visible>!String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9341).NumPages,1)</visible>\n                <top>122</top>\n                <height>38</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="textbox">\n                        <height>38</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>38</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9342).NumPages,1) + !String.IsEqual(Container(9341).NumPages,1)</visible>\n                <top>105</top>\n                <height>73</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="textbox">\n                        <height>73</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>73</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9343).NumPages,1) + !String.IsEqual(Container(9342).NumPages,1)</visible>\n                <top>87</top>\n                <height>108</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="textbox">\n                        <height>108</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>108</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9344).NumPages,1) + !String.IsEqual(Container(9343).NumPages,1)</visible>\n                <top>70</top>\n                <height>143</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="textbox">\n                        <height>143</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>143</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9345).NumPages,1) + !String.IsEqual(Container(9344).NumPages,1)</visible>\n                <top>52</top>\n                <height>178</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="textbox">\n                        <height>178</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>178</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9346).NumPages,1) + !String.IsEqual(Container(9345).NumPages,1)</visible>\n                <top>35</top>\n                <height>213</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="textbox">\n                        <height>213</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>213</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9347).NumPages,1) + !String.IsEqual(Container(9346).NumPages,1)</visible>\n                <top>17</top>\n                <height>248</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="textbox">\n                        <height>248</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>248</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container(301).ListItem.DBType,episode) + !String.IsEqual(Container(9347).NumPages,1)</visible>\n                <top>0</top>\n                <height>283</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="textbox">\n                        <height>283</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <autoscroll delay="8000" time="3000" repeat="10000">true</autoscroll>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>283</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <autoscroll delay="8000" time="3000" repeat="10000">true</autoscroll>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9341).NumPages,1)</visible>\n                <top>95</top>\n                <height>92</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="label">\n                        <height>44</height>\n                        <font>font_main_bold</font>\n                        <textcolor>main_fg_100</textcolor>\n                        <label>$INFO[Container(301).ListItem.Season,S,]$INFO[Container(301).ListItem.Episode,E, · ]$INFO[Container(301).ListItem.Title]</label>\n                    </control>\n                    <control type="textbox">\n                        <height>38</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>38</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9342).NumPages,1) + !String.IsEqual(Container(9341).NumPages,1)</visible>\n                <top>78</top>\n                <height>127</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="label">\n                        <height>44</height>\n                        <font>font_main_bold</font>\n                        <textcolor>main_fg_100</textcolor>\n                        <label>$INFO[Container(301).ListItem.Season,S,]$INFO[Container(301).ListItem.Episode,E, · ]$INFO[Container(301).ListItem.Title]</label>\n                    </control>\n                    <control type="textbox">\n                        <height>73</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>73</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9343).NumPages,1) + !String.IsEqual(Container(9342).NumPages,1)</visible>\n                <top>60</top>\n                <height>162</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="label">\n                        <height>44</height>\n                        <font>font_main_bold</font>\n                        <textcolor>main_fg_100</textcolor>\n                        <label>$INFO[Container(301).ListItem.Season,S,]$INFO[Container(301).ListItem.Episode,E, · ]$INFO[Container(301).ListItem.Title]</label>\n                    </control>\n                    <control type="textbox">\n                        <height>108</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>108</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9344).NumPages,1) + !String.IsEqual(Container(9343).NumPages,1)</visible>\n                <top>43</top>\n                <height>197</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="label">\n                        <height>44</height>\n                        <font>font_main_bold</font>\n                        <textcolor>main_fg_100</textcolor>\n                        <label>$INFO[Container(301).ListItem.Season,S,]$INFO[Container(301).ListItem.Episode,E, · ]$INFO[Container(301).ListItem.Title]</label>\n                    </control>\n                    <control type="textbox">\n                        <height>143</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>143</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9345).NumPages,1) + !String.IsEqual(Container(9344).NumPages,1)</visible>\n                <top>25</top>\n                <height>232</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="label">\n                        <height>44</height>\n                        <font>font_main_bold</font>\n                        <textcolor>main_fg_100</textcolor>\n                        <label>$INFO[Container(301).ListItem.Season,S,]$INFO[Container(301).ListItem.Episode,E, · ]$INFO[Container(301).ListItem.Title]</label>\n                    </control>\n                    <control type="textbox">\n                        <height>178</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>178</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9346).NumPages,1) + !String.IsEqual(Container(9345).NumPages,1)</visible>\n                <top>8</top>\n                <height>267</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="label">\n                        <height>44</height>\n                        <font>font_main_bold</font>\n                        <textcolor>main_fg_100</textcolor>\n                        <label>$INFO[Container(301).ListItem.Season,S,]$INFO[Container(301).ListItem.Episode,E, · ]$INFO[Container(301).ListItem.Title]</label>\n                    </control>\n                    <control type="textbox">\n                        <height>213</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>213</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9347).NumPages,1) + !String.IsEqual(Container(9346).NumPages,1)</visible>\n                <top>0</top>\n                <height>283</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="label">\n                        <height>44</height>\n                        <font>font_main_bold</font>\n                        <textcolor>main_fg_100</textcolor>\n                        <label>$INFO[Container(301).ListItem.Season,S,]$INFO[Container(301).ListItem.Episode,E, · ]$INFO[Container(301).ListItem.Title]</label>\n                    </control>\n                    <control type="textbox">\n                        <height>229</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <autoscroll delay="8000" time="3000" repeat="10000">true</autoscroll>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>229</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <autoscroll delay="8000" time="3000" repeat="10000">true</autoscroll>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container(301).ListItem.DBType,episode) + !String.IsEqual(Container(9347).NumPages,1)</visible>\n                <top>0</top>\n                <height>283</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="label">\n                        <height>44</height>\n                        <font>font_main_bold</font>\n                        <textcolor>main_fg_100</textcolor>\n                        <label>$INFO[Container(301).ListItem.Season,S,]$INFO[Container(301).ListItem.Episode,E, · ]$INFO[Container(301).ListItem.Title]</label>\n                    </control>\n                    <control type="textbox">\n                        <height>229</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <autoscroll delay="8000" time="3000" repeat="10000">true</autoscroll>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>229</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <autoscroll delay="8000" time="3000" repeat="10000">true</autoscroll>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n        </control>\n        <control type="group">',
        'already_patched_check': '<!-- ABUKARIM: plot on the right -->\n        <control type="group">\n            <visible>Skin.HasSetting(abk.plotright) + !$EXP[Exp_InfoDialogs]',
        'description': 'AF3 Plot on the Right - Spotlight: plot box on the right',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes_Hubs.xml'),
        'not_found_ok': True,
        'old': '<include name="Hub_Combined_Info">\n        <control type="group">',
        'new': '<include name="Hub_Combined_Info">\n        <!-- ABUKARIM: plot on the right -->\n        <control type="group">\n            <visible>Skin.HasSetting(abk.plotright) + !$EXP[Exp_Hubs_SlideInfo] + !$EXP[Exp_InfoDialogs] + !$EXP[Hub_Spotlight_Visible_Expression] + Integer.IsEqual(Window.Property(TMDBHelper.WidgetContainer),$PARAM[id]) + !String.IsEmpty(Container($PARAM[id]).ListItem.Plot)</visible>\n            <include>Home_Info_Animation</include>\n            <right>120</right>\n            <width>700</width>\n            <top>179</top>\n            <height>283</height>\n            <!-- ABUKARIM: plot box 4.6.21 (hub info): glass inside the page margin, centred on the info column -->\n            <!-- probes: invisible copies of the plot, one per line count (line = 35 px);\n                 Container(id).NumPages = 1 when the plot fits that height -->\n            <control type="textbox" id="93$PARAM[id]1">\n                <width>700</width>\n                <height>38</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n            </control>\n            <control type="textbox" id="93$PARAM[id]2">\n                <width>700</width>\n                <height>73</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n            </control>\n            <control type="textbox" id="93$PARAM[id]3">\n                <width>700</width>\n                <height>108</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n            </control>\n            <control type="textbox" id="93$PARAM[id]4">\n                <width>700</width>\n                <height>143</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n            </control>\n            <control type="textbox" id="93$PARAM[id]5">\n                <width>700</width>\n                <height>178</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n            </control>\n            <control type="textbox" id="93$PARAM[id]6">\n                <width>700</width>\n                <height>213</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n            </control>\n            <control type="textbox" id="93$PARAM[id]7">\n                <width>700</width>\n                <height>248</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n            </control>\n            <!-- the box: the smallest height that holds the plot, centred on the info column -->\n            <control type="group">\n                <visible>!String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(93$PARAM[id]1).NumPages,1)</visible>\n                <top>122</top>\n                <height>38</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="textbox">\n                        <height>38</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>38</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(93$PARAM[id]2).NumPages,1) + !String.IsEqual(Container(93$PARAM[id]1).NumPages,1)</visible>\n                <top>105</top>\n                <height>73</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="textbox">\n                        <height>73</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>73</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(93$PARAM[id]3).NumPages,1) + !String.IsEqual(Container(93$PARAM[id]2).NumPages,1)</visible>\n                <top>87</top>\n                <height>108</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="textbox">\n                        <height>108</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>108</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(93$PARAM[id]4).NumPages,1) + !String.IsEqual(Container(93$PARAM[id]3).NumPages,1)</visible>\n                <top>70</top>\n                <height>143</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="textbox">\n                        <height>143</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>143</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(93$PARAM[id]5).NumPages,1) + !String.IsEqual(Container(93$PARAM[id]4).NumPages,1)</visible>\n                <top>52</top>\n                <height>178</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="textbox">\n                        <height>178</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>178</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(93$PARAM[id]6).NumPages,1) + !String.IsEqual(Container(93$PARAM[id]5).NumPages,1)</visible>\n                <top>35</top>\n                <height>213</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="textbox">\n                        <height>213</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>213</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(93$PARAM[id]7).NumPages,1) + !String.IsEqual(Container(93$PARAM[id]6).NumPages,1)</visible>\n                <top>17</top>\n                <height>248</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="textbox">\n                        <height>248</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>248</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + !String.IsEqual(Container(93$PARAM[id]7).NumPages,1)</visible>\n                <top>0</top>\n                <height>283</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="textbox">\n                        <height>283</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <autoscroll delay="8000" time="3000" repeat="10000">true</autoscroll>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>283</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <autoscroll delay="8000" time="3000" repeat="10000">true</autoscroll>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(93$PARAM[id]1).NumPages,1)</visible>\n                <top>95</top>\n                <height>92</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="label">\n                        <height>44</height>\n                        <font>font_main_bold</font>\n                        <textcolor>main_fg_100</textcolor>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Season,S,]$INFO[Container($PARAM[id]).ListItem.Episode,E, · ]$INFO[Container($PARAM[id]).ListItem.Title]</label>\n                    </control>\n                    <control type="textbox">\n                        <height>38</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>38</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(93$PARAM[id]2).NumPages,1) + !String.IsEqual(Container(93$PARAM[id]1).NumPages,1)</visible>\n                <top>78</top>\n                <height>127</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="label">\n                        <height>44</height>\n                        <font>font_main_bold</font>\n                        <textcolor>main_fg_100</textcolor>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Season,S,]$INFO[Container($PARAM[id]).ListItem.Episode,E, · ]$INFO[Container($PARAM[id]).ListItem.Title]</label>\n                    </control>\n                    <control type="textbox">\n                        <height>73</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>73</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(93$PARAM[id]3).NumPages,1) + !String.IsEqual(Container(93$PARAM[id]2).NumPages,1)</visible>\n                <top>60</top>\n                <height>162</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="label">\n                        <height>44</height>\n                        <font>font_main_bold</font>\n                        <textcolor>main_fg_100</textcolor>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Season,S,]$INFO[Container($PARAM[id]).ListItem.Episode,E, · ]$INFO[Container($PARAM[id]).ListItem.Title]</label>\n                    </control>\n                    <control type="textbox">\n                        <height>108</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>108</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(93$PARAM[id]4).NumPages,1) + !String.IsEqual(Container(93$PARAM[id]3).NumPages,1)</visible>\n                <top>43</top>\n                <height>197</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="label">\n                        <height>44</height>\n                        <font>font_main_bold</font>\n                        <textcolor>main_fg_100</textcolor>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Season,S,]$INFO[Container($PARAM[id]).ListItem.Episode,E, · ]$INFO[Container($PARAM[id]).ListItem.Title]</label>\n                    </control>\n                    <control type="textbox">\n                        <height>143</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>143</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(93$PARAM[id]5).NumPages,1) + !String.IsEqual(Container(93$PARAM[id]4).NumPages,1)</visible>\n                <top>25</top>\n                <height>232</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="label">\n                        <height>44</height>\n                        <font>font_main_bold</font>\n                        <textcolor>main_fg_100</textcolor>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Season,S,]$INFO[Container($PARAM[id]).ListItem.Episode,E, · ]$INFO[Container($PARAM[id]).ListItem.Title]</label>\n                    </control>\n                    <control type="textbox">\n                        <height>178</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>178</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(93$PARAM[id]6).NumPages,1) + !String.IsEqual(Container(93$PARAM[id]5).NumPages,1)</visible>\n                <top>8</top>\n                <height>267</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="label">\n                        <height>44</height>\n                        <font>font_main_bold</font>\n                        <textcolor>main_fg_100</textcolor>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Season,S,]$INFO[Container($PARAM[id]).ListItem.Episode,E, · ]$INFO[Container($PARAM[id]).ListItem.Title]</label>\n                    </control>\n                    <control type="textbox">\n                        <height>213</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>213</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(93$PARAM[id]7).NumPages,1) + !String.IsEqual(Container(93$PARAM[id]6).NumPages,1)</visible>\n                <top>0</top>\n                <height>283</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="label">\n                        <height>44</height>\n                        <font>font_main_bold</font>\n                        <textcolor>main_fg_100</textcolor>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Season,S,]$INFO[Container($PARAM[id]).ListItem.Episode,E, · ]$INFO[Container($PARAM[id]).ListItem.Title]</label>\n                    </control>\n                    <control type="textbox">\n                        <height>229</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <autoscroll delay="8000" time="3000" repeat="10000">true</autoscroll>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>229</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <autoscroll delay="8000" time="3000" repeat="10000">true</autoscroll>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + !String.IsEqual(Container(93$PARAM[id]7).NumPages,1)</visible>\n                <top>0</top>\n                <height>283</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="label">\n                        <height>44</height>\n                        <font>font_main_bold</font>\n                        <textcolor>main_fg_100</textcolor>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Season,S,]$INFO[Container($PARAM[id]).ListItem.Episode,E, · ]$INFO[Container($PARAM[id]).ListItem.Title]</label>\n                    </control>\n                    <control type="textbox">\n                        <height>229</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <autoscroll delay="8000" time="3000" repeat="10000">true</autoscroll>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>229</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <autoscroll delay="8000" time="3000" repeat="10000">true</autoscroll>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n        </control>\n        <control type="group">',
        'already_patched_check': '<!-- ABUKARIM: plot on the right -->\n        <control type="group">\n            <visible>Skin.HasSetting(abk.plotright) + !$EXP[Exp_Hubs_SlideInfo]',
        'description': 'AF3 Plot on the Right - hub info: plot box on the right',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes_Hubs.xml'),
        'not_found_ok': True,
        'old': '<param name="visible_plot">String.IsEmpty(Window(Home).Property(Background.ShowOverlay))</param>',
        'new': '<param name="visible_plot">String.IsEmpty(Window(Home).Property(Background.ShowOverlay)) + !Skin.HasSetting(abk.plotright)</param>',
        'already_patched_check': 'ShowOverlay)) + !Skin.HasSetting(abk.plotright)</param>',
        'description': 'AF3 Plot on the Right - Spotlight: left plot off',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes_Hubs.xml'),
        'not_found_ok': True,
        'old': '<param name="visible_plot">true</param>\n                    <param name="visible_meta">true</param>\n                    <param name="include_title">false</param>',
        'new': '<param name="visible_plot">!Skin.HasSetting(abk.plotright)</param>\n                    <param name="visible_meta">true</param>\n                    <param name="include_title">false</param>',
        'already_patched_check': '<param name="visible_plot">!Skin.HasSetting(abk.plotright)</param>',
        'description': 'AF3 Plot on the Right - hub info: left plot off',
    },

    # 4.6.16: the genre line (AF3 "Plotline" = Genre) is drawn INSIDE the plot
    # block, so hiding the plot took it away (screenshot 2026-10-31). Info_Panel
    # gets a param plotright_genre (default false) and its own genre line under
    # the info line; the two Home callers pass Skin.HasSetting(abk.plotright).
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes_Info.xml'),
        'not_found_ok': True,
        'old': '        <param name="visible_plot">true</param>\n        <param name="visible_meta">true</param>\n        <param name="listitem">ListItem</param>\n        <definition>',
        'new': '        <param name="visible_plot">true</param>\n        <param name="visible_meta">true</param>\n        <param name="listitem">ListItem</param>\n        <param name="plotright_genre">false</param>  <!-- ABUKARIM: genre line (plot on the right) -->\n        <definition>',
        'already_patched_check': '<param name="plotright_genre">false</param>',
        'description': 'AF3 Plot on the Right - Info_Panel genre param',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes_Info.xml'),
        'not_found_ok': True,
        'old': '                <!-- Info -->\n                <include content="Info_Line" condition="$PARAM[include_details]">\n',
        'new': '                <!-- ABUKARIM: genre under the title (plot on the right) -->\n                <control type="group">\n                    <visible>$PARAM[plotright_genre] + !String.IsEmpty($PARAM[container]$PARAM[listitem].Genre)</visible>\n                    <height>39</height>\n                    <control type="label">\n                        <left>40</left>\n                        <top>6</top>\n                        <height>40</height>\n                        <width>$PARAM[plotwidth]</width>\n                        <font>font_main_bold</font>\n                        <textcolor>$PARAM[colordiffuse]_90</textcolor>\n                        <label>$INFO[$PARAM[container]$PARAM[listitem].Genre]</label>\n                    </control>\n                </control>\n\n                <!-- Info -->\n                <include content="Info_Line" condition="$PARAM[include_details]">\n',
        'already_patched_check': '<!-- ABUKARIM: genre under the title (plot on the right) -->',
        'description': 'AF3 Plot on the Right - Info_Panel genre line',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes_Hubs.xml'),
        'not_found_ok': True,
        'old': '<param name="visible_plot">!Skin.HasSetting(abk.plotright)</param>',
        'new': '<param name="visible_plot">!Skin.HasSetting(abk.plotright)</param>\n                    <param name="plotright_genre">Skin.HasSetting(abk.plotright)</param>',
        'already_patched_check': '<param name="visible_plot">!Skin.HasSetting(abk.plotright)</param>\n                    <param name="plotright_genre">Skin.HasSetting(abk.plotright)</param>',
        'description': 'AF3 Plot on the Right - hub info: genre line on the left',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes_Hubs.xml'),
        'not_found_ok': True,
        'old': '<param name="visible_plot">String.IsEmpty(Window(Home).Property(Background.ShowOverlay)) + !Skin.HasSetting(abk.plotright)</param>',
        'new': '<param name="visible_plot">String.IsEmpty(Window(Home).Property(Background.ShowOverlay)) + !Skin.HasSetting(abk.plotright)</param>\n                <param name="plotright_genre">String.IsEmpty(Window(Home).Property(Background.ShowOverlay)) + Skin.HasSetting(abk.plotright)</param>',
        'already_patched_check': '<param name="plotright_genre">String.IsEmpty(',
        'description': 'AF3 Plot on the Right - Spotlight: genre line on the left',
    },

    # 4.6.17: the Spotlight box started level with the logo and covered the end
    # of a long info line (flags, stars, date, duration - screenshot
    # 2026-10-31 06:48). It now starts under the info line and ends above the
    # widget heading (top 431, height 178; glass padding 22 instead of 34).
    # The two entries below move a box written by 4.6.15 / 4.6.16.
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes_Hubs.xml'),
        'not_found_ok': True,
        'old': '        <!-- ABUKARIM: plot on the right -->\n        <control type="group">\n            <visible>Skin.HasSetting(abk.plotright) + !$EXP[Exp_InfoDialogs] + $EXP[Hub_Spotlight_Visible_Expression] + String.IsEmpty(Window(Home).Property(Background.ShowOverlay)) + !String.IsEmpty(Container(301).ListItem.Plot)</visible>\n            <animation effect="slide" end="0" start="0,-200" time="400" tween="cubic" easing="out" reversible="false" condition="!Control.HasFocus(300)">Visible</animation>\n            <animation effect="slide" start="0" end="0,-200" time="400" tween="cubic" easing="out" reversible="false">Hidden</animation>\n            <right>view_pad</right>\n            <width>700</width>\n            <top>300</top>\n            <height>340</height>\n            <control type="image">\n                <left>-40</left>\n                <top>-34</top>\n                <right>-40</right>\n                <bottom>-34</bottom>\n                <texture border="48">abk_lucent/panel.png</texture>\n                <colordiffuse>panel_bg_70</colordiffuse>\n            </control>\n            <control type="image">\n                <left>-40</left>\n                <top>-34</top>\n                <right>-40</right>\n                <bottom>-34</bottom>\n                <texture border="48">abk_lucent/panel_edge.png</texture>\n                <colordiffuse>overlay_hard</colordiffuse>\n            </control>\n            <control type="grouplist">\n                <orientation>vertical</orientation>\n                <itemgap>10</itemgap>\n                <control type="label">\n                    <height>44</height>\n                    <font>font_main_bold</font>\n                    <textcolor>main_fg_100</textcolor>\n                    <label>$INFO[Container(301).ListItem.Season,S,]$INFO[Container(301).ListItem.Episode,E, · ]$INFO[Container(301).ListItem.Title]</label>\n                    <visible>String.IsEqual(Container(301).ListItem.DBType,episode)</visible>\n                </control>\n                <control type="textbox">\n                    <height>286</height>\n                    <font>font_mini_plot</font>\n                    <textcolor>main_fg_90</textcolor>\n                    <align>right</align>\n                    <label>$INFO[Container(301).ListItem.Plot]</label>\n                    <autoscroll delay="8000" time="3000" repeat="10000">true</autoscroll>\n                    <visible>String.StartsWith(System.Language,Arabic)</visible>\n                </control>\n                <control type="textbox">\n                    <height>286</height>\n                    <font>font_mini_plot</font>\n                    <textcolor>main_fg_90</textcolor>\n                    <align>left</align>\n                    <label>$INFO[Container(301).ListItem.Plot]</label>\n                    <autoscroll delay="8000" time="3000" repeat="10000">true</autoscroll>\n                    <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                </control>\n            </control>\n        </control>\n',
        'new': '        <!-- ABUKARIM: plot on the right -->\n        <control type="group">\n            <visible>Skin.HasSetting(abk.plotright) + !$EXP[Exp_InfoDialogs] + $EXP[Hub_Spotlight_Visible_Expression] + String.IsEmpty(Window(Home).Property(Background.ShowOverlay)) + !String.IsEmpty(Container(301).ListItem.Plot)</visible>\n            <animation effect="slide" end="0" start="0,-200" time="400" tween="cubic" easing="out" reversible="false" condition="!Control.HasFocus(300)">Visible</animation>\n            <animation effect="slide" start="0" end="0,-200" time="400" tween="cubic" easing="out" reversible="false">Hidden</animation>\n            <right>120</right>\n            <width>700</width>\n            <top>164</top>\n            <height>283</height>\n            <!-- ABUKARIM: plot box 4.6.21 (Spotlight): glass inside the page margin, centred on the info column -->\n            <!-- probes: invisible copies of the plot, one per line count (line = 35 px);\n                 Container(id).NumPages = 1 when the plot fits that height -->\n            <control type="textbox" id="9341">\n                <width>700</width>\n                <height>38</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container(301).ListItem.Plot]</label>\n            </control>\n            <control type="textbox" id="9342">\n                <width>700</width>\n                <height>73</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container(301).ListItem.Plot]</label>\n            </control>\n            <control type="textbox" id="9343">\n                <width>700</width>\n                <height>108</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container(301).ListItem.Plot]</label>\n            </control>\n            <control type="textbox" id="9344">\n                <width>700</width>\n                <height>143</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container(301).ListItem.Plot]</label>\n            </control>\n            <control type="textbox" id="9345">\n                <width>700</width>\n                <height>178</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container(301).ListItem.Plot]</label>\n            </control>\n            <control type="textbox" id="9346">\n                <width>700</width>\n                <height>213</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container(301).ListItem.Plot]</label>\n            </control>\n            <control type="textbox" id="9347">\n                <width>700</width>\n                <height>248</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container(301).ListItem.Plot]</label>\n            </control>\n            <!-- the box: the smallest height that holds the plot, centred on the info column -->\n            <control type="group">\n                <visible>!String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9341).NumPages,1)</visible>\n                <top>122</top>\n                <height>38</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="textbox">\n                        <height>38</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>38</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9342).NumPages,1) + !String.IsEqual(Container(9341).NumPages,1)</visible>\n                <top>105</top>\n                <height>73</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="textbox">\n                        <height>73</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>73</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9343).NumPages,1) + !String.IsEqual(Container(9342).NumPages,1)</visible>\n                <top>87</top>\n                <height>108</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="textbox">\n                        <height>108</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>108</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9344).NumPages,1) + !String.IsEqual(Container(9343).NumPages,1)</visible>\n                <top>70</top>\n                <height>143</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="textbox">\n                        <height>143</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>143</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9345).NumPages,1) + !String.IsEqual(Container(9344).NumPages,1)</visible>\n                <top>52</top>\n                <height>178</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="textbox">\n                        <height>178</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>178</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9346).NumPages,1) + !String.IsEqual(Container(9345).NumPages,1)</visible>\n                <top>35</top>\n                <height>213</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="textbox">\n                        <height>213</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>213</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9347).NumPages,1) + !String.IsEqual(Container(9346).NumPages,1)</visible>\n                <top>17</top>\n                <height>248</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="textbox">\n                        <height>248</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>248</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container(301).ListItem.DBType,episode) + !String.IsEqual(Container(9347).NumPages,1)</visible>\n                <top>0</top>\n                <height>283</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="textbox">\n                        <height>283</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <autoscroll delay="8000" time="3000" repeat="10000">true</autoscroll>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>283</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <autoscroll delay="8000" time="3000" repeat="10000">true</autoscroll>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9341).NumPages,1)</visible>\n                <top>95</top>\n                <height>92</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="label">\n                        <height>44</height>\n                        <font>font_main_bold</font>\n                        <textcolor>main_fg_100</textcolor>\n                        <label>$INFO[Container(301).ListItem.Season,S,]$INFO[Container(301).ListItem.Episode,E, · ]$INFO[Container(301).ListItem.Title]</label>\n                    </control>\n                    <control type="textbox">\n                        <height>38</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>38</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9342).NumPages,1) + !String.IsEqual(Container(9341).NumPages,1)</visible>\n                <top>78</top>\n                <height>127</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="label">\n                        <height>44</height>\n                        <font>font_main_bold</font>\n                        <textcolor>main_fg_100</textcolor>\n                        <label>$INFO[Container(301).ListItem.Season,S,]$INFO[Container(301).ListItem.Episode,E, · ]$INFO[Container(301).ListItem.Title]</label>\n                    </control>\n                    <control type="textbox">\n                        <height>73</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>73</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9343).NumPages,1) + !String.IsEqual(Container(9342).NumPages,1)</visible>\n                <top>60</top>\n                <height>162</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="label">\n                        <height>44</height>\n                        <font>font_main_bold</font>\n                        <textcolor>main_fg_100</textcolor>\n                        <label>$INFO[Container(301).ListItem.Season,S,]$INFO[Container(301).ListItem.Episode,E, · ]$INFO[Container(301).ListItem.Title]</label>\n                    </control>\n                    <control type="textbox">\n                        <height>108</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>108</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9344).NumPages,1) + !String.IsEqual(Container(9343).NumPages,1)</visible>\n                <top>43</top>\n                <height>197</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="label">\n                        <height>44</height>\n                        <font>font_main_bold</font>\n                        <textcolor>main_fg_100</textcolor>\n                        <label>$INFO[Container(301).ListItem.Season,S,]$INFO[Container(301).ListItem.Episode,E, · ]$INFO[Container(301).ListItem.Title]</label>\n                    </control>\n                    <control type="textbox">\n                        <height>143</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>143</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9345).NumPages,1) + !String.IsEqual(Container(9344).NumPages,1)</visible>\n                <top>25</top>\n                <height>232</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="label">\n                        <height>44</height>\n                        <font>font_main_bold</font>\n                        <textcolor>main_fg_100</textcolor>\n                        <label>$INFO[Container(301).ListItem.Season,S,]$INFO[Container(301).ListItem.Episode,E, · ]$INFO[Container(301).ListItem.Title]</label>\n                    </control>\n                    <control type="textbox">\n                        <height>178</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>178</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9346).NumPages,1) + !String.IsEqual(Container(9345).NumPages,1)</visible>\n                <top>8</top>\n                <height>267</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="label">\n                        <height>44</height>\n                        <font>font_main_bold</font>\n                        <textcolor>main_fg_100</textcolor>\n                        <label>$INFO[Container(301).ListItem.Season,S,]$INFO[Container(301).ListItem.Episode,E, · ]$INFO[Container(301).ListItem.Title]</label>\n                    </control>\n                    <control type="textbox">\n                        <height>213</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>213</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9347).NumPages,1) + !String.IsEqual(Container(9346).NumPages,1)</visible>\n                <top>0</top>\n                <height>283</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="label">\n                        <height>44</height>\n                        <font>font_main_bold</font>\n                        <textcolor>main_fg_100</textcolor>\n                        <label>$INFO[Container(301).ListItem.Season,S,]$INFO[Container(301).ListItem.Episode,E, · ]$INFO[Container(301).ListItem.Title]</label>\n                    </control>\n                    <control type="textbox">\n                        <height>229</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <autoscroll delay="8000" time="3000" repeat="10000">true</autoscroll>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>229</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <autoscroll delay="8000" time="3000" repeat="10000">true</autoscroll>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container(301).ListItem.DBType,episode) + !String.IsEqual(Container(9347).NumPages,1)</visible>\n                <top>0</top>\n                <height>283</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="label">\n                        <height>44</height>\n                        <font>font_main_bold</font>\n                        <textcolor>main_fg_100</textcolor>\n                        <label>$INFO[Container(301).ListItem.Season,S,]$INFO[Container(301).ListItem.Episode,E, · ]$INFO[Container(301).ListItem.Title]</label>\n                    </control>\n                    <control type="textbox">\n                        <height>229</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <autoscroll delay="8000" time="3000" repeat="10000">true</autoscroll>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>229</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <autoscroll delay="8000" time="3000" repeat="10000">true</autoscroll>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n        </control>\n',
        'already_patched_check': '<!-- ABUKARIM: plot box 4.6.21 (Spotlight): glass inside the page margin, centred on the info column -->',
        'description': 'AF3 Plot on the Right - Spotlight box under the info line (upgrade)',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes_Hubs.xml'),
        'not_found_ok': True,
        'old': '        <!-- ABUKARIM: plot on the right -->\n        <control type="group">\n            <visible>Skin.HasSetting(abk.plotright) + !$EXP[Exp_Hubs_SlideInfo] + !$EXP[Exp_InfoDialogs] + !$EXP[Hub_Spotlight_Visible_Expression] + Integer.IsEqual(Window.Property(TMDBHelper.WidgetContainer),$PARAM[id]) + !String.IsEmpty(Container($PARAM[id]).ListItem.Plot)</visible>\n            <include>Home_Info_Animation</include>\n            <right>view_pad</right>\n            <width>700</width>\n            <top>200</top>\n            <height>300</height>\n            <control type="image">\n                <left>-40</left>\n                <top>-34</top>\n                <right>-40</right>\n                <bottom>-34</bottom>\n                <texture border="48">abk_lucent/panel.png</texture>\n                <colordiffuse>panel_bg_70</colordiffuse>\n            </control>\n            <control type="image">\n                <left>-40</left>\n                <top>-34</top>\n                <right>-40</right>\n                <bottom>-34</bottom>\n                <texture border="48">abk_lucent/panel_edge.png</texture>\n                <colordiffuse>overlay_hard</colordiffuse>\n            </control>\n            <control type="grouplist">\n                <orientation>vertical</orientation>\n                <itemgap>10</itemgap>\n                <control type="label">\n                    <height>44</height>\n                    <font>font_main_bold</font>\n                    <textcolor>main_fg_100</textcolor>\n                    <label>$INFO[Container($PARAM[id]).ListItem.Season,S,]$INFO[Container($PARAM[id]).ListItem.Episode,E, · ]$INFO[Container($PARAM[id]).ListItem.Title]</label>\n                    <visible>String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode)</visible>\n                </control>\n                <control type="textbox">\n                    <height>246</height>\n                    <font>font_mini_plot</font>\n                    <textcolor>main_fg_90</textcolor>\n                    <align>right</align>\n                    <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                    <autoscroll delay="8000" time="3000" repeat="10000">true</autoscroll>\n                    <visible>String.StartsWith(System.Language,Arabic)</visible>\n                </control>\n                <control type="textbox">\n                    <height>246</height>\n                    <font>font_mini_plot</font>\n                    <textcolor>main_fg_90</textcolor>\n                    <align>left</align>\n                    <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                    <autoscroll delay="8000" time="3000" repeat="10000">true</autoscroll>\n                    <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                </control>\n            </control>\n        </control>\n',
        'new': '        <!-- ABUKARIM: plot on the right -->\n        <control type="group">\n            <visible>Skin.HasSetting(abk.plotright) + !$EXP[Exp_Hubs_SlideInfo] + !$EXP[Exp_InfoDialogs] + !$EXP[Hub_Spotlight_Visible_Expression] + Integer.IsEqual(Window.Property(TMDBHelper.WidgetContainer),$PARAM[id]) + !String.IsEmpty(Container($PARAM[id]).ListItem.Plot)</visible>\n            <include>Home_Info_Animation</include>\n            <right>120</right>\n            <width>700</width>\n            <top>179</top>\n            <height>283</height>\n            <!-- ABUKARIM: plot box 4.6.21 (hub info): glass inside the page margin, centred on the info column -->\n            <!-- probes: invisible copies of the plot, one per line count (line = 35 px);\n                 Container(id).NumPages = 1 when the plot fits that height -->\n            <control type="textbox" id="93$PARAM[id]1">\n                <width>700</width>\n                <height>38</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n            </control>\n            <control type="textbox" id="93$PARAM[id]2">\n                <width>700</width>\n                <height>73</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n            </control>\n            <control type="textbox" id="93$PARAM[id]3">\n                <width>700</width>\n                <height>108</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n            </control>\n            <control type="textbox" id="93$PARAM[id]4">\n                <width>700</width>\n                <height>143</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n            </control>\n            <control type="textbox" id="93$PARAM[id]5">\n                <width>700</width>\n                <height>178</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n            </control>\n            <control type="textbox" id="93$PARAM[id]6">\n                <width>700</width>\n                <height>213</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n            </control>\n            <control type="textbox" id="93$PARAM[id]7">\n                <width>700</width>\n                <height>248</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n            </control>\n            <!-- the box: the smallest height that holds the plot, centred on the info column -->\n            <control type="group">\n                <visible>!String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(93$PARAM[id]1).NumPages,1)</visible>\n                <top>122</top>\n                <height>38</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="textbox">\n                        <height>38</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>38</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(93$PARAM[id]2).NumPages,1) + !String.IsEqual(Container(93$PARAM[id]1).NumPages,1)</visible>\n                <top>105</top>\n                <height>73</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="textbox">\n                        <height>73</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>73</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(93$PARAM[id]3).NumPages,1) + !String.IsEqual(Container(93$PARAM[id]2).NumPages,1)</visible>\n                <top>87</top>\n                <height>108</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="textbox">\n                        <height>108</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>108</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(93$PARAM[id]4).NumPages,1) + !String.IsEqual(Container(93$PARAM[id]3).NumPages,1)</visible>\n                <top>70</top>\n                <height>143</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="textbox">\n                        <height>143</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>143</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(93$PARAM[id]5).NumPages,1) + !String.IsEqual(Container(93$PARAM[id]4).NumPages,1)</visible>\n                <top>52</top>\n                <height>178</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="textbox">\n                        <height>178</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>178</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(93$PARAM[id]6).NumPages,1) + !String.IsEqual(Container(93$PARAM[id]5).NumPages,1)</visible>\n                <top>35</top>\n                <height>213</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="textbox">\n                        <height>213</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>213</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(93$PARAM[id]7).NumPages,1) + !String.IsEqual(Container(93$PARAM[id]6).NumPages,1)</visible>\n                <top>17</top>\n                <height>248</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="textbox">\n                        <height>248</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>248</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + !String.IsEqual(Container(93$PARAM[id]7).NumPages,1)</visible>\n                <top>0</top>\n                <height>283</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="textbox">\n                        <height>283</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <autoscroll delay="8000" time="3000" repeat="10000">true</autoscroll>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>283</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <autoscroll delay="8000" time="3000" repeat="10000">true</autoscroll>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(93$PARAM[id]1).NumPages,1)</visible>\n                <top>95</top>\n                <height>92</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="label">\n                        <height>44</height>\n                        <font>font_main_bold</font>\n                        <textcolor>main_fg_100</textcolor>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Season,S,]$INFO[Container($PARAM[id]).ListItem.Episode,E, · ]$INFO[Container($PARAM[id]).ListItem.Title]</label>\n                    </control>\n                    <control type="textbox">\n                        <height>38</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>38</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(93$PARAM[id]2).NumPages,1) + !String.IsEqual(Container(93$PARAM[id]1).NumPages,1)</visible>\n                <top>78</top>\n                <height>127</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="label">\n                        <height>44</height>\n                        <font>font_main_bold</font>\n                        <textcolor>main_fg_100</textcolor>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Season,S,]$INFO[Container($PARAM[id]).ListItem.Episode,E, · ]$INFO[Container($PARAM[id]).ListItem.Title]</label>\n                    </control>\n                    <control type="textbox">\n                        <height>73</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>73</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(93$PARAM[id]3).NumPages,1) + !String.IsEqual(Container(93$PARAM[id]2).NumPages,1)</visible>\n                <top>60</top>\n                <height>162</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="label">\n                        <height>44</height>\n                        <font>font_main_bold</font>\n                        <textcolor>main_fg_100</textcolor>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Season,S,]$INFO[Container($PARAM[id]).ListItem.Episode,E, · ]$INFO[Container($PARAM[id]).ListItem.Title]</label>\n                    </control>\n                    <control type="textbox">\n                        <height>108</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>108</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(93$PARAM[id]4).NumPages,1) + !String.IsEqual(Container(93$PARAM[id]3).NumPages,1)</visible>\n                <top>43</top>\n                <height>197</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="label">\n                        <height>44</height>\n                        <font>font_main_bold</font>\n                        <textcolor>main_fg_100</textcolor>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Season,S,]$INFO[Container($PARAM[id]).ListItem.Episode,E, · ]$INFO[Container($PARAM[id]).ListItem.Title]</label>\n                    </control>\n                    <control type="textbox">\n                        <height>143</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>143</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(93$PARAM[id]5).NumPages,1) + !String.IsEqual(Container(93$PARAM[id]4).NumPages,1)</visible>\n                <top>25</top>\n                <height>232</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="label">\n                        <height>44</height>\n                        <font>font_main_bold</font>\n                        <textcolor>main_fg_100</textcolor>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Season,S,]$INFO[Container($PARAM[id]).ListItem.Episode,E, · ]$INFO[Container($PARAM[id]).ListItem.Title]</label>\n                    </control>\n                    <control type="textbox">\n                        <height>178</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>178</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(93$PARAM[id]6).NumPages,1) + !String.IsEqual(Container(93$PARAM[id]5).NumPages,1)</visible>\n                <top>8</top>\n                <height>267</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="label">\n                        <height>44</height>\n                        <font>font_main_bold</font>\n                        <textcolor>main_fg_100</textcolor>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Season,S,]$INFO[Container($PARAM[id]).ListItem.Episode,E, · ]$INFO[Container($PARAM[id]).ListItem.Title]</label>\n                    </control>\n                    <control type="textbox">\n                        <height>213</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>213</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(93$PARAM[id]7).NumPages,1) + !String.IsEqual(Container(93$PARAM[id]6).NumPages,1)</visible>\n                <top>0</top>\n                <height>283</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="label">\n                        <height>44</height>\n                        <font>font_main_bold</font>\n                        <textcolor>main_fg_100</textcolor>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Season,S,]$INFO[Container($PARAM[id]).ListItem.Episode,E, · ]$INFO[Container($PARAM[id]).ListItem.Title]</label>\n                    </control>\n                    <control type="textbox">\n                        <height>229</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <autoscroll delay="8000" time="3000" repeat="10000">true</autoscroll>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>229</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <autoscroll delay="8000" time="3000" repeat="10000">true</autoscroll>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + !String.IsEqual(Container(93$PARAM[id]7).NumPages,1)</visible>\n                <top>0</top>\n                <height>283</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="label">\n                        <height>44</height>\n                        <font>font_main_bold</font>\n                        <textcolor>main_fg_100</textcolor>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Season,S,]$INFO[Container($PARAM[id]).ListItem.Episode,E, · ]$INFO[Container($PARAM[id]).ListItem.Title]</label>\n                    </control>\n                    <control type="textbox">\n                        <height>229</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <autoscroll delay="8000" time="3000" repeat="10000">true</autoscroll>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>229</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <autoscroll delay="8000" time="3000" repeat="10000">true</autoscroll>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n        </control>\n',
        'already_patched_check': '<!-- ABUKARIM: plot box 4.6.21 (hub info): glass inside the page margin, centred on the info column -->',
        'description': 'AF3 Plot on the Right - hub info box padding (upgrade)',
    },

    # 4.6.18: the glass fits the plot. Invisible probe textboxes (same text /
    # font / width, heights 40..max) report Container(id).NumPages; the glass
    # takes the smallest height whose probe holds the whole plot (one page).
    # No font metrics needed; if NumPages were unavailable every probe is
    # false and the glass stays at the max height (the 4.6.17 behaviour).
    # Lighter glass (panel_bg_50 + overlay_soft edge). With the switch on the
    # Two-line information bar is on (af3_plotright_toggle), so the info line
    # is short again and the Spotlight box goes back up to the logo (top 300,
    # up to 300 high) - it only grows as far as the plot needs.
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes_Hubs.xml'),
        'not_found_ok': True,
        'old': '        <!-- ABUKARIM: plot on the right -->\n        <control type="group">\n            <visible>Skin.HasSetting(abk.plotright) + !$EXP[Exp_InfoDialogs] + $EXP[Hub_Spotlight_Visible_Expression] + String.IsEmpty(Window(Home).Property(Background.ShowOverlay)) + !String.IsEmpty(Container(301).ListItem.Plot)</visible>\n            <animation effect="slide" end="0" start="0,-200" time="400" tween="cubic" easing="out" reversible="false" condition="!Control.HasFocus(300)">Visible</animation>\n            <animation effect="slide" start="0" end="0,-200" time="400" tween="cubic" easing="out" reversible="false">Hidden</animation>\n            <right>view_pad</right>\n            <width>700</width>\n            <top>431</top>\n            <height>178</height>\n            <control type="image">\n                <left>-40</left>\n                <top>-22</top>\n                <right>-40</right>\n                <bottom>-22</bottom>\n                <texture border="48">abk_lucent/panel.png</texture>\n                <colordiffuse>panel_bg_70</colordiffuse>\n            </control>\n            <control type="image">\n                <left>-40</left>\n                <top>-22</top>\n                <right>-40</right>\n                <bottom>-22</bottom>\n                <texture border="48">abk_lucent/panel_edge.png</texture>\n                <colordiffuse>overlay_hard</colordiffuse>\n            </control>\n            <control type="grouplist">\n                <orientation>vertical</orientation>\n                <itemgap>10</itemgap>\n                <control type="label">\n                    <height>44</height>\n                    <font>font_main_bold</font>\n                    <textcolor>main_fg_100</textcolor>\n                    <label>$INFO[Container(301).ListItem.Season,S,]$INFO[Container(301).ListItem.Episode,E, · ]$INFO[Container(301).ListItem.Title]</label>\n                    <visible>String.IsEqual(Container(301).ListItem.DBType,episode)</visible>\n                </control>\n                <control type="textbox">\n                    <height>124</height>\n                    <font>font_mini_plot</font>\n                    <textcolor>main_fg_90</textcolor>\n                    <align>right</align>\n                    <label>$INFO[Container(301).ListItem.Plot]</label>\n                    <autoscroll delay="8000" time="3000" repeat="10000">true</autoscroll>\n                    <visible>String.StartsWith(System.Language,Arabic)</visible>\n                </control>\n                <control type="textbox">\n                    <height>124</height>\n                    <font>font_mini_plot</font>\n                    <textcolor>main_fg_90</textcolor>\n                    <align>left</align>\n                    <label>$INFO[Container(301).ListItem.Plot]</label>\n                    <autoscroll delay="8000" time="3000" repeat="10000">true</autoscroll>\n                    <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                </control>\n            </control>\n        </control>\n',
        'new': '        <!-- ABUKARIM: plot on the right -->\n        <control type="group">\n            <visible>Skin.HasSetting(abk.plotright) + !$EXP[Exp_InfoDialogs] + $EXP[Hub_Spotlight_Visible_Expression] + String.IsEmpty(Window(Home).Property(Background.ShowOverlay)) + !String.IsEmpty(Container(301).ListItem.Plot)</visible>\n            <animation effect="slide" end="0" start="0,-200" time="400" tween="cubic" easing="out" reversible="false" condition="!Control.HasFocus(300)">Visible</animation>\n            <animation effect="slide" start="0" end="0,-200" time="400" tween="cubic" easing="out" reversible="false">Hidden</animation>\n            <right>120</right>\n            <width>700</width>\n            <top>164</top>\n            <height>283</height>\n            <!-- ABUKARIM: plot box 4.6.21 (Spotlight): glass inside the page margin, centred on the info column -->\n            <!-- probes: invisible copies of the plot, one per line count (line = 35 px);\n                 Container(id).NumPages = 1 when the plot fits that height -->\n            <control type="textbox" id="9341">\n                <width>700</width>\n                <height>38</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container(301).ListItem.Plot]</label>\n            </control>\n            <control type="textbox" id="9342">\n                <width>700</width>\n                <height>73</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container(301).ListItem.Plot]</label>\n            </control>\n            <control type="textbox" id="9343">\n                <width>700</width>\n                <height>108</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container(301).ListItem.Plot]</label>\n            </control>\n            <control type="textbox" id="9344">\n                <width>700</width>\n                <height>143</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container(301).ListItem.Plot]</label>\n            </control>\n            <control type="textbox" id="9345">\n                <width>700</width>\n                <height>178</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container(301).ListItem.Plot]</label>\n            </control>\n            <control type="textbox" id="9346">\n                <width>700</width>\n                <height>213</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container(301).ListItem.Plot]</label>\n            </control>\n            <control type="textbox" id="9347">\n                <width>700</width>\n                <height>248</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container(301).ListItem.Plot]</label>\n            </control>\n            <!-- the box: the smallest height that holds the plot, centred on the info column -->\n            <control type="group">\n                <visible>!String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9341).NumPages,1)</visible>\n                <top>122</top>\n                <height>38</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="textbox">\n                        <height>38</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>38</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9342).NumPages,1) + !String.IsEqual(Container(9341).NumPages,1)</visible>\n                <top>105</top>\n                <height>73</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="textbox">\n                        <height>73</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>73</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9343).NumPages,1) + !String.IsEqual(Container(9342).NumPages,1)</visible>\n                <top>87</top>\n                <height>108</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="textbox">\n                        <height>108</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>108</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9344).NumPages,1) + !String.IsEqual(Container(9343).NumPages,1)</visible>\n                <top>70</top>\n                <height>143</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="textbox">\n                        <height>143</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>143</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9345).NumPages,1) + !String.IsEqual(Container(9344).NumPages,1)</visible>\n                <top>52</top>\n                <height>178</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="textbox">\n                        <height>178</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>178</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9346).NumPages,1) + !String.IsEqual(Container(9345).NumPages,1)</visible>\n                <top>35</top>\n                <height>213</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="textbox">\n                        <height>213</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>213</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9347).NumPages,1) + !String.IsEqual(Container(9346).NumPages,1)</visible>\n                <top>17</top>\n                <height>248</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="textbox">\n                        <height>248</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>248</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container(301).ListItem.DBType,episode) + !String.IsEqual(Container(9347).NumPages,1)</visible>\n                <top>0</top>\n                <height>283</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="textbox">\n                        <height>283</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <autoscroll delay="8000" time="3000" repeat="10000">true</autoscroll>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>283</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <autoscroll delay="8000" time="3000" repeat="10000">true</autoscroll>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9341).NumPages,1)</visible>\n                <top>95</top>\n                <height>92</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="label">\n                        <height>44</height>\n                        <font>font_main_bold</font>\n                        <textcolor>main_fg_100</textcolor>\n                        <label>$INFO[Container(301).ListItem.Season,S,]$INFO[Container(301).ListItem.Episode,E, · ]$INFO[Container(301).ListItem.Title]</label>\n                    </control>\n                    <control type="textbox">\n                        <height>38</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>38</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9342).NumPages,1) + !String.IsEqual(Container(9341).NumPages,1)</visible>\n                <top>78</top>\n                <height>127</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="label">\n                        <height>44</height>\n                        <font>font_main_bold</font>\n                        <textcolor>main_fg_100</textcolor>\n                        <label>$INFO[Container(301).ListItem.Season,S,]$INFO[Container(301).ListItem.Episode,E, · ]$INFO[Container(301).ListItem.Title]</label>\n                    </control>\n                    <control type="textbox">\n                        <height>73</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>73</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9343).NumPages,1) + !String.IsEqual(Container(9342).NumPages,1)</visible>\n                <top>60</top>\n                <height>162</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="label">\n                        <height>44</height>\n                        <font>font_main_bold</font>\n                        <textcolor>main_fg_100</textcolor>\n                        <label>$INFO[Container(301).ListItem.Season,S,]$INFO[Container(301).ListItem.Episode,E, · ]$INFO[Container(301).ListItem.Title]</label>\n                    </control>\n                    <control type="textbox">\n                        <height>108</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>108</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9344).NumPages,1) + !String.IsEqual(Container(9343).NumPages,1)</visible>\n                <top>43</top>\n                <height>197</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="label">\n                        <height>44</height>\n                        <font>font_main_bold</font>\n                        <textcolor>main_fg_100</textcolor>\n                        <label>$INFO[Container(301).ListItem.Season,S,]$INFO[Container(301).ListItem.Episode,E, · ]$INFO[Container(301).ListItem.Title]</label>\n                    </control>\n                    <control type="textbox">\n                        <height>143</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>143</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9345).NumPages,1) + !String.IsEqual(Container(9344).NumPages,1)</visible>\n                <top>25</top>\n                <height>232</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="label">\n                        <height>44</height>\n                        <font>font_main_bold</font>\n                        <textcolor>main_fg_100</textcolor>\n                        <label>$INFO[Container(301).ListItem.Season,S,]$INFO[Container(301).ListItem.Episode,E, · ]$INFO[Container(301).ListItem.Title]</label>\n                    </control>\n                    <control type="textbox">\n                        <height>178</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>178</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9346).NumPages,1) + !String.IsEqual(Container(9345).NumPages,1)</visible>\n                <top>8</top>\n                <height>267</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="label">\n                        <height>44</height>\n                        <font>font_main_bold</font>\n                        <textcolor>main_fg_100</textcolor>\n                        <label>$INFO[Container(301).ListItem.Season,S,]$INFO[Container(301).ListItem.Episode,E, · ]$INFO[Container(301).ListItem.Title]</label>\n                    </control>\n                    <control type="textbox">\n                        <height>213</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>213</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9347).NumPages,1) + !String.IsEqual(Container(9346).NumPages,1)</visible>\n                <top>0</top>\n                <height>283</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="label">\n                        <height>44</height>\n                        <font>font_main_bold</font>\n                        <textcolor>main_fg_100</textcolor>\n                        <label>$INFO[Container(301).ListItem.Season,S,]$INFO[Container(301).ListItem.Episode,E, · ]$INFO[Container(301).ListItem.Title]</label>\n                    </control>\n                    <control type="textbox">\n                        <height>229</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <autoscroll delay="8000" time="3000" repeat="10000">true</autoscroll>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>229</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <autoscroll delay="8000" time="3000" repeat="10000">true</autoscroll>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container(301).ListItem.DBType,episode) + !String.IsEqual(Container(9347).NumPages,1)</visible>\n                <top>0</top>\n                <height>283</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="label">\n                        <height>44</height>\n                        <font>font_main_bold</font>\n                        <textcolor>main_fg_100</textcolor>\n                        <label>$INFO[Container(301).ListItem.Season,S,]$INFO[Container(301).ListItem.Episode,E, · ]$INFO[Container(301).ListItem.Title]</label>\n                    </control>\n                    <control type="textbox">\n                        <height>229</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <autoscroll delay="8000" time="3000" repeat="10000">true</autoscroll>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>229</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <autoscroll delay="8000" time="3000" repeat="10000">true</autoscroll>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n        </control>\n',
        'already_patched_check': '<!-- ABUKARIM: plot box 4.6.21 (Spotlight): glass inside the page margin, centred on the info column -->',
        'description': 'AF3 Plot on the Right - Spotlight box fits the plot (upgrade from 4.6.17)',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes_Hubs.xml'),
        'not_found_ok': True,
        'old': '        <!-- ABUKARIM: plot on the right -->\n        <control type="group">\n            <visible>Skin.HasSetting(abk.plotright) + !$EXP[Exp_Hubs_SlideInfo] + !$EXP[Exp_InfoDialogs] + !$EXP[Hub_Spotlight_Visible_Expression] + Integer.IsEqual(Window.Property(TMDBHelper.WidgetContainer),$PARAM[id]) + !String.IsEmpty(Container($PARAM[id]).ListItem.Plot)</visible>\n            <include>Home_Info_Animation</include>\n            <right>view_pad</right>\n            <width>700</width>\n            <top>200</top>\n            <height>300</height>\n            <control type="image">\n                <left>-40</left>\n                <top>-22</top>\n                <right>-40</right>\n                <bottom>-22</bottom>\n                <texture border="48">abk_lucent/panel.png</texture>\n                <colordiffuse>panel_bg_70</colordiffuse>\n            </control>\n            <control type="image">\n                <left>-40</left>\n                <top>-22</top>\n                <right>-40</right>\n                <bottom>-22</bottom>\n                <texture border="48">abk_lucent/panel_edge.png</texture>\n                <colordiffuse>overlay_hard</colordiffuse>\n            </control>\n            <control type="grouplist">\n                <orientation>vertical</orientation>\n                <itemgap>10</itemgap>\n                <control type="label">\n                    <height>44</height>\n                    <font>font_main_bold</font>\n                    <textcolor>main_fg_100</textcolor>\n                    <label>$INFO[Container($PARAM[id]).ListItem.Season,S,]$INFO[Container($PARAM[id]).ListItem.Episode,E, · ]$INFO[Container($PARAM[id]).ListItem.Title]</label>\n                    <visible>String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode)</visible>\n                </control>\n                <control type="textbox">\n                    <height>246</height>\n                    <font>font_mini_plot</font>\n                    <textcolor>main_fg_90</textcolor>\n                    <align>right</align>\n                    <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                    <autoscroll delay="8000" time="3000" repeat="10000">true</autoscroll>\n                    <visible>String.StartsWith(System.Language,Arabic)</visible>\n                </control>\n                <control type="textbox">\n                    <height>246</height>\n                    <font>font_mini_plot</font>\n                    <textcolor>main_fg_90</textcolor>\n                    <align>left</align>\n                    <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                    <autoscroll delay="8000" time="3000" repeat="10000">true</autoscroll>\n                    <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                </control>\n            </control>\n        </control>\n',
        'new': '        <!-- ABUKARIM: plot on the right -->\n        <control type="group">\n            <visible>Skin.HasSetting(abk.plotright) + !$EXP[Exp_Hubs_SlideInfo] + !$EXP[Exp_InfoDialogs] + !$EXP[Hub_Spotlight_Visible_Expression] + Integer.IsEqual(Window.Property(TMDBHelper.WidgetContainer),$PARAM[id]) + !String.IsEmpty(Container($PARAM[id]).ListItem.Plot)</visible>\n            <include>Home_Info_Animation</include>\n            <right>120</right>\n            <width>700</width>\n            <top>179</top>\n            <height>283</height>\n            <!-- ABUKARIM: plot box 4.6.21 (hub info): glass inside the page margin, centred on the info column -->\n            <!-- probes: invisible copies of the plot, one per line count (line = 35 px);\n                 Container(id).NumPages = 1 when the plot fits that height -->\n            <control type="textbox" id="93$PARAM[id]1">\n                <width>700</width>\n                <height>38</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n            </control>\n            <control type="textbox" id="93$PARAM[id]2">\n                <width>700</width>\n                <height>73</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n            </control>\n            <control type="textbox" id="93$PARAM[id]3">\n                <width>700</width>\n                <height>108</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n            </control>\n            <control type="textbox" id="93$PARAM[id]4">\n                <width>700</width>\n                <height>143</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n            </control>\n            <control type="textbox" id="93$PARAM[id]5">\n                <width>700</width>\n                <height>178</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n            </control>\n            <control type="textbox" id="93$PARAM[id]6">\n                <width>700</width>\n                <height>213</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n            </control>\n            <control type="textbox" id="93$PARAM[id]7">\n                <width>700</width>\n                <height>248</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n            </control>\n            <!-- the box: the smallest height that holds the plot, centred on the info column -->\n            <control type="group">\n                <visible>!String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(93$PARAM[id]1).NumPages,1)</visible>\n                <top>122</top>\n                <height>38</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="textbox">\n                        <height>38</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>38</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(93$PARAM[id]2).NumPages,1) + !String.IsEqual(Container(93$PARAM[id]1).NumPages,1)</visible>\n                <top>105</top>\n                <height>73</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="textbox">\n                        <height>73</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>73</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(93$PARAM[id]3).NumPages,1) + !String.IsEqual(Container(93$PARAM[id]2).NumPages,1)</visible>\n                <top>87</top>\n                <height>108</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="textbox">\n                        <height>108</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>108</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(93$PARAM[id]4).NumPages,1) + !String.IsEqual(Container(93$PARAM[id]3).NumPages,1)</visible>\n                <top>70</top>\n                <height>143</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="textbox">\n                        <height>143</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>143</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(93$PARAM[id]5).NumPages,1) + !String.IsEqual(Container(93$PARAM[id]4).NumPages,1)</visible>\n                <top>52</top>\n                <height>178</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="textbox">\n                        <height>178</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>178</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(93$PARAM[id]6).NumPages,1) + !String.IsEqual(Container(93$PARAM[id]5).NumPages,1)</visible>\n                <top>35</top>\n                <height>213</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="textbox">\n                        <height>213</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>213</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(93$PARAM[id]7).NumPages,1) + !String.IsEqual(Container(93$PARAM[id]6).NumPages,1)</visible>\n                <top>17</top>\n                <height>248</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="textbox">\n                        <height>248</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>248</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + !String.IsEqual(Container(93$PARAM[id]7).NumPages,1)</visible>\n                <top>0</top>\n                <height>283</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="textbox">\n                        <height>283</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <autoscroll delay="8000" time="3000" repeat="10000">true</autoscroll>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>283</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <autoscroll delay="8000" time="3000" repeat="10000">true</autoscroll>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(93$PARAM[id]1).NumPages,1)</visible>\n                <top>95</top>\n                <height>92</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="label">\n                        <height>44</height>\n                        <font>font_main_bold</font>\n                        <textcolor>main_fg_100</textcolor>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Season,S,]$INFO[Container($PARAM[id]).ListItem.Episode,E, · ]$INFO[Container($PARAM[id]).ListItem.Title]</label>\n                    </control>\n                    <control type="textbox">\n                        <height>38</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>38</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(93$PARAM[id]2).NumPages,1) + !String.IsEqual(Container(93$PARAM[id]1).NumPages,1)</visible>\n                <top>78</top>\n                <height>127</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="label">\n                        <height>44</height>\n                        <font>font_main_bold</font>\n                        <textcolor>main_fg_100</textcolor>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Season,S,]$INFO[Container($PARAM[id]).ListItem.Episode,E, · ]$INFO[Container($PARAM[id]).ListItem.Title]</label>\n                    </control>\n                    <control type="textbox">\n                        <height>73</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>73</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(93$PARAM[id]3).NumPages,1) + !String.IsEqual(Container(93$PARAM[id]2).NumPages,1)</visible>\n                <top>60</top>\n                <height>162</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="label">\n                        <height>44</height>\n                        <font>font_main_bold</font>\n                        <textcolor>main_fg_100</textcolor>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Season,S,]$INFO[Container($PARAM[id]).ListItem.Episode,E, · ]$INFO[Container($PARAM[id]).ListItem.Title]</label>\n                    </control>\n                    <control type="textbox">\n                        <height>108</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>108</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(93$PARAM[id]4).NumPages,1) + !String.IsEqual(Container(93$PARAM[id]3).NumPages,1)</visible>\n                <top>43</top>\n                <height>197</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="label">\n                        <height>44</height>\n                        <font>font_main_bold</font>\n                        <textcolor>main_fg_100</textcolor>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Season,S,]$INFO[Container($PARAM[id]).ListItem.Episode,E, · ]$INFO[Container($PARAM[id]).ListItem.Title]</label>\n                    </control>\n                    <control type="textbox">\n                        <height>143</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>143</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(93$PARAM[id]5).NumPages,1) + !String.IsEqual(Container(93$PARAM[id]4).NumPages,1)</visible>\n                <top>25</top>\n                <height>232</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="label">\n                        <height>44</height>\n                        <font>font_main_bold</font>\n                        <textcolor>main_fg_100</textcolor>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Season,S,]$INFO[Container($PARAM[id]).ListItem.Episode,E, · ]$INFO[Container($PARAM[id]).ListItem.Title]</label>\n                    </control>\n                    <control type="textbox">\n                        <height>178</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>178</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(93$PARAM[id]6).NumPages,1) + !String.IsEqual(Container(93$PARAM[id]5).NumPages,1)</visible>\n                <top>8</top>\n                <height>267</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="label">\n                        <height>44</height>\n                        <font>font_main_bold</font>\n                        <textcolor>main_fg_100</textcolor>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Season,S,]$INFO[Container($PARAM[id]).ListItem.Episode,E, · ]$INFO[Container($PARAM[id]).ListItem.Title]</label>\n                    </control>\n                    <control type="textbox">\n                        <height>213</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>213</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(93$PARAM[id]7).NumPages,1) + !String.IsEqual(Container(93$PARAM[id]6).NumPages,1)</visible>\n                <top>0</top>\n                <height>283</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="label">\n                        <height>44</height>\n                        <font>font_main_bold</font>\n                        <textcolor>main_fg_100</textcolor>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Season,S,]$INFO[Container($PARAM[id]).ListItem.Episode,E, · ]$INFO[Container($PARAM[id]).ListItem.Title]</label>\n                    </control>\n                    <control type="textbox">\n                        <height>229</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <autoscroll delay="8000" time="3000" repeat="10000">true</autoscroll>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>229</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <autoscroll delay="8000" time="3000" repeat="10000">true</autoscroll>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + !String.IsEqual(Container(93$PARAM[id]7).NumPages,1)</visible>\n                <top>0</top>\n                <height>283</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="label">\n                        <height>44</height>\n                        <font>font_main_bold</font>\n                        <textcolor>main_fg_100</textcolor>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Season,S,]$INFO[Container($PARAM[id]).ListItem.Episode,E, · ]$INFO[Container($PARAM[id]).ListItem.Title]</label>\n                    </control>\n                    <control type="textbox">\n                        <height>229</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <autoscroll delay="8000" time="3000" repeat="10000">true</autoscroll>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>229</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <autoscroll delay="8000" time="3000" repeat="10000">true</autoscroll>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n        </control>\n',
        'already_patched_check': '<!-- ABUKARIM: plot box 4.6.21 (hub info): glass inside the page margin, centred on the info column -->',
        'description': 'AF3 Plot on the Right - hub info box fits the plot (upgrade from 4.6.17)',
    },

    # 4.6.19: tidy layout. The box is centred on the info column (logo to the
    # ratings row) and grows / shrinks around that centre; the probe heights
    # are whole lines of the plot font (35 px), so the glass hugs the text with
    # the same padding on every side (40 / 30). The genre line sits on AF3's
    # 40 px two-line info bar rhythm (info line - genre - ratings evenly
    # spaced).
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes_Hubs.xml'),
        'not_found_ok': True,
        'old': '        <!-- ABUKARIM: plot on the right -->\n        <control type="group">\n            <visible>Skin.HasSetting(abk.plotright) + !$EXP[Exp_InfoDialogs] + $EXP[Hub_Spotlight_Visible_Expression] + String.IsEmpty(Window(Home).Property(Background.ShowOverlay)) + !String.IsEmpty(Container(301).ListItem.Plot)</visible>\n            <animation effect="slide" end="0" start="0,-200" time="400" tween="cubic" easing="out" reversible="false" condition="!Control.HasFocus(300)">Visible</animation>\n            <animation effect="slide" start="0" end="0,-200" time="400" tween="cubic" easing="out" reversible="false">Hidden</animation>\n            <right>view_pad</right>\n            <width>700</width>\n            <top>300</top>\n            <height>300</height>\n            <!-- ABUKARIM: plot box fits the plot (4.6.18) -->\n            <!-- probes: invisible copies of the plot; Container(id).NumPages = 1 when it fits that height -->\n            <control type="textbox" id="9301">\n                <width>700</width>\n                <height>40</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container(301).ListItem.Plot]</label>\n            </control>\n            <control type="textbox" id="9302">\n                <width>700</width>\n                <height>76</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container(301).ListItem.Plot]</label>\n            </control>\n            <control type="textbox" id="9303">\n                <width>700</width>\n                <height>112</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container(301).ListItem.Plot]</label>\n            </control>\n            <control type="textbox" id="9304">\n                <width>700</width>\n                <height>148</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container(301).ListItem.Plot]</label>\n            </control>\n            <control type="textbox" id="9305">\n                <width>700</width>\n                <height>184</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container(301).ListItem.Plot]</label>\n            </control>\n            <control type="textbox" id="9306">\n                <width>700</width>\n                <height>220</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container(301).ListItem.Plot]</label>\n            </control>\n            <control type="textbox" id="9307">\n                <width>700</width>\n                <height>256</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container(301).ListItem.Plot]</label>\n            </control>\n            <control type="textbox" id="9308">\n                <width>700</width>\n                <height>292</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container(301).ListItem.Plot]</label>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9301).NumPages,1)</visible>\n                <height>40</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-22</top>\n                    <right>-40</right>\n                    <bottom>-22</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-22</top>\n                    <right>-40</right>\n                    <bottom>-22</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9302).NumPages,1) + !String.IsEqual(Container(9301).NumPages,1)</visible>\n                <height>76</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-22</top>\n                    <right>-40</right>\n                    <bottom>-22</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-22</top>\n                    <right>-40</right>\n                    <bottom>-22</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9303).NumPages,1) + !String.IsEqual(Container(9302).NumPages,1)</visible>\n                <height>112</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-22</top>\n                    <right>-40</right>\n                    <bottom>-22</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-22</top>\n                    <right>-40</right>\n                    <bottom>-22</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9304).NumPages,1) + !String.IsEqual(Container(9303).NumPages,1)</visible>\n                <height>148</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-22</top>\n                    <right>-40</right>\n                    <bottom>-22</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-22</top>\n                    <right>-40</right>\n                    <bottom>-22</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9305).NumPages,1) + !String.IsEqual(Container(9304).NumPages,1)</visible>\n                <height>184</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-22</top>\n                    <right>-40</right>\n                    <bottom>-22</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-22</top>\n                    <right>-40</right>\n                    <bottom>-22</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9306).NumPages,1) + !String.IsEqual(Container(9305).NumPages,1)</visible>\n                <height>220</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-22</top>\n                    <right>-40</right>\n                    <bottom>-22</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-22</top>\n                    <right>-40</right>\n                    <bottom>-22</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9307).NumPages,1) + !String.IsEqual(Container(9306).NumPages,1)</visible>\n                <height>256</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-22</top>\n                    <right>-40</right>\n                    <bottom>-22</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-22</top>\n                    <right>-40</right>\n                    <bottom>-22</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9308).NumPages,1) + !String.IsEqual(Container(9307).NumPages,1)</visible>\n                <height>292</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-22</top>\n                    <right>-40</right>\n                    <bottom>-22</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-22</top>\n                    <right>-40</right>\n                    <bottom>-22</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container(301).ListItem.DBType,episode) + !String.IsEqual(Container(9308).NumPages,1)</visible>\n                <height>300</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-22</top>\n                    <right>-40</right>\n                    <bottom>-22</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-22</top>\n                    <right>-40</right>\n                    <bottom>-22</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9301).NumPages,1)</visible>\n                <height>94</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-22</top>\n                    <right>-40</right>\n                    <bottom>-22</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-22</top>\n                    <right>-40</right>\n                    <bottom>-22</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9302).NumPages,1) + !String.IsEqual(Container(9301).NumPages,1)</visible>\n                <height>130</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-22</top>\n                    <right>-40</right>\n                    <bottom>-22</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-22</top>\n                    <right>-40</right>\n                    <bottom>-22</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9303).NumPages,1) + !String.IsEqual(Container(9302).NumPages,1)</visible>\n                <height>166</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-22</top>\n                    <right>-40</right>\n                    <bottom>-22</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-22</top>\n                    <right>-40</right>\n                    <bottom>-22</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9304).NumPages,1) + !String.IsEqual(Container(9303).NumPages,1)</visible>\n                <height>202</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-22</top>\n                    <right>-40</right>\n                    <bottom>-22</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-22</top>\n                    <right>-40</right>\n                    <bottom>-22</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9305).NumPages,1) + !String.IsEqual(Container(9304).NumPages,1)</visible>\n                <height>238</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-22</top>\n                    <right>-40</right>\n                    <bottom>-22</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-22</top>\n                    <right>-40</right>\n                    <bottom>-22</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9306).NumPages,1) + !String.IsEqual(Container(9305).NumPages,1)</visible>\n                <height>274</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-22</top>\n                    <right>-40</right>\n                    <bottom>-22</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-22</top>\n                    <right>-40</right>\n                    <bottom>-22</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9307).NumPages,1) + !String.IsEqual(Container(9306).NumPages,1)</visible>\n                <height>300</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-22</top>\n                    <right>-40</right>\n                    <bottom>-22</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-22</top>\n                    <right>-40</right>\n                    <bottom>-22</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9308).NumPages,1) + !String.IsEqual(Container(9307).NumPages,1)</visible>\n                <height>300</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-22</top>\n                    <right>-40</right>\n                    <bottom>-22</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-22</top>\n                    <right>-40</right>\n                    <bottom>-22</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container(301).ListItem.DBType,episode) + !String.IsEqual(Container(9308).NumPages,1)</visible>\n                <height>300</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-22</top>\n                    <right>-40</right>\n                    <bottom>-22</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-22</top>\n                    <right>-40</right>\n                    <bottom>-22</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n            </control>\n            <control type="grouplist">\n                <orientation>vertical</orientation>\n                <itemgap>10</itemgap>\n                <control type="label">\n                    <height>44</height>\n                    <font>font_main_bold</font>\n                    <textcolor>main_fg_100</textcolor>\n                    <label>$INFO[Container(301).ListItem.Season,S,]$INFO[Container(301).ListItem.Episode,E, · ]$INFO[Container(301).ListItem.Title]</label>\n                    <visible>String.IsEqual(Container(301).ListItem.DBType,episode)</visible>\n                </control>\n                <control type="textbox">\n                    <height>300</height>\n                    <font>font_mini_plot</font>\n                    <textcolor>main_fg_90</textcolor>\n                    <align>right</align>\n                    <label>$INFO[Container(301).ListItem.Plot]</label>\n                    <autoscroll delay="8000" time="3000" repeat="10000">true</autoscroll>\n                    <visible>String.StartsWith(System.Language,Arabic) + !String.IsEqual(Container(301).ListItem.DBType,episode)</visible>\n                </control>\n                <control type="textbox">\n                    <height>246</height>\n                    <font>font_mini_plot</font>\n                    <textcolor>main_fg_90</textcolor>\n                    <align>right</align>\n                    <label>$INFO[Container(301).ListItem.Plot]</label>\n                    <autoscroll delay="8000" time="3000" repeat="10000">true</autoscroll>\n                    <visible>String.StartsWith(System.Language,Arabic) + String.IsEqual(Container(301).ListItem.DBType,episode)</visible>\n                </control>\n                <control type="textbox">\n                    <height>300</height>\n                    <font>font_mini_plot</font>\n                    <textcolor>main_fg_90</textcolor>\n                    <align>left</align>\n                    <label>$INFO[Container(301).ListItem.Plot]</label>\n                    <autoscroll delay="8000" time="3000" repeat="10000">true</autoscroll>\n                    <visible>!String.StartsWith(System.Language,Arabic) + !String.IsEqual(Container(301).ListItem.DBType,episode)</visible>\n                </control>\n                <control type="textbox">\n                    <height>246</height>\n                    <font>font_mini_plot</font>\n                    <textcolor>main_fg_90</textcolor>\n                    <align>left</align>\n                    <label>$INFO[Container(301).ListItem.Plot]</label>\n                    <autoscroll delay="8000" time="3000" repeat="10000">true</autoscroll>\n                    <visible>!String.StartsWith(System.Language,Arabic) + String.IsEqual(Container(301).ListItem.DBType,episode)</visible>\n                </control>\n            </control>\n        </control>\n',
        'new': '        <!-- ABUKARIM: plot on the right -->\n        <control type="group">\n            <visible>Skin.HasSetting(abk.plotright) + !$EXP[Exp_InfoDialogs] + $EXP[Hub_Spotlight_Visible_Expression] + String.IsEmpty(Window(Home).Property(Background.ShowOverlay)) + !String.IsEmpty(Container(301).ListItem.Plot)</visible>\n            <animation effect="slide" end="0" start="0,-200" time="400" tween="cubic" easing="out" reversible="false" condition="!Control.HasFocus(300)">Visible</animation>\n            <animation effect="slide" start="0" end="0,-200" time="400" tween="cubic" easing="out" reversible="false">Hidden</animation>\n            <right>120</right>\n            <width>700</width>\n            <top>164</top>\n            <height>283</height>\n            <!-- ABUKARIM: plot box 4.6.21 (Spotlight): glass inside the page margin, centred on the info column -->\n            <!-- probes: invisible copies of the plot, one per line count (line = 35 px);\n                 Container(id).NumPages = 1 when the plot fits that height -->\n            <control type="textbox" id="9341">\n                <width>700</width>\n                <height>38</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container(301).ListItem.Plot]</label>\n            </control>\n            <control type="textbox" id="9342">\n                <width>700</width>\n                <height>73</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container(301).ListItem.Plot]</label>\n            </control>\n            <control type="textbox" id="9343">\n                <width>700</width>\n                <height>108</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container(301).ListItem.Plot]</label>\n            </control>\n            <control type="textbox" id="9344">\n                <width>700</width>\n                <height>143</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container(301).ListItem.Plot]</label>\n            </control>\n            <control type="textbox" id="9345">\n                <width>700</width>\n                <height>178</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container(301).ListItem.Plot]</label>\n            </control>\n            <control type="textbox" id="9346">\n                <width>700</width>\n                <height>213</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container(301).ListItem.Plot]</label>\n            </control>\n            <control type="textbox" id="9347">\n                <width>700</width>\n                <height>248</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container(301).ListItem.Plot]</label>\n            </control>\n            <!-- the box: the smallest height that holds the plot, centred on the info column -->\n            <control type="group">\n                <visible>!String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9341).NumPages,1)</visible>\n                <top>122</top>\n                <height>38</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="textbox">\n                        <height>38</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>38</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9342).NumPages,1) + !String.IsEqual(Container(9341).NumPages,1)</visible>\n                <top>105</top>\n                <height>73</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="textbox">\n                        <height>73</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>73</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9343).NumPages,1) + !String.IsEqual(Container(9342).NumPages,1)</visible>\n                <top>87</top>\n                <height>108</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="textbox">\n                        <height>108</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>108</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9344).NumPages,1) + !String.IsEqual(Container(9343).NumPages,1)</visible>\n                <top>70</top>\n                <height>143</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="textbox">\n                        <height>143</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>143</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9345).NumPages,1) + !String.IsEqual(Container(9344).NumPages,1)</visible>\n                <top>52</top>\n                <height>178</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="textbox">\n                        <height>178</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>178</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9346).NumPages,1) + !String.IsEqual(Container(9345).NumPages,1)</visible>\n                <top>35</top>\n                <height>213</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="textbox">\n                        <height>213</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>213</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9347).NumPages,1) + !String.IsEqual(Container(9346).NumPages,1)</visible>\n                <top>17</top>\n                <height>248</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="textbox">\n                        <height>248</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>248</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container(301).ListItem.DBType,episode) + !String.IsEqual(Container(9347).NumPages,1)</visible>\n                <top>0</top>\n                <height>283</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="textbox">\n                        <height>283</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <autoscroll delay="8000" time="3000" repeat="10000">true</autoscroll>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>283</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <autoscroll delay="8000" time="3000" repeat="10000">true</autoscroll>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9341).NumPages,1)</visible>\n                <top>95</top>\n                <height>92</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="label">\n                        <height>44</height>\n                        <font>font_main_bold</font>\n                        <textcolor>main_fg_100</textcolor>\n                        <label>$INFO[Container(301).ListItem.Season,S,]$INFO[Container(301).ListItem.Episode,E, · ]$INFO[Container(301).ListItem.Title]</label>\n                    </control>\n                    <control type="textbox">\n                        <height>38</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>38</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9342).NumPages,1) + !String.IsEqual(Container(9341).NumPages,1)</visible>\n                <top>78</top>\n                <height>127</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="label">\n                        <height>44</height>\n                        <font>font_main_bold</font>\n                        <textcolor>main_fg_100</textcolor>\n                        <label>$INFO[Container(301).ListItem.Season,S,]$INFO[Container(301).ListItem.Episode,E, · ]$INFO[Container(301).ListItem.Title]</label>\n                    </control>\n                    <control type="textbox">\n                        <height>73</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>73</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9343).NumPages,1) + !String.IsEqual(Container(9342).NumPages,1)</visible>\n                <top>60</top>\n                <height>162</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="label">\n                        <height>44</height>\n                        <font>font_main_bold</font>\n                        <textcolor>main_fg_100</textcolor>\n                        <label>$INFO[Container(301).ListItem.Season,S,]$INFO[Container(301).ListItem.Episode,E, · ]$INFO[Container(301).ListItem.Title]</label>\n                    </control>\n                    <control type="textbox">\n                        <height>108</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>108</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9344).NumPages,1) + !String.IsEqual(Container(9343).NumPages,1)</visible>\n                <top>43</top>\n                <height>197</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="label">\n                        <height>44</height>\n                        <font>font_main_bold</font>\n                        <textcolor>main_fg_100</textcolor>\n                        <label>$INFO[Container(301).ListItem.Season,S,]$INFO[Container(301).ListItem.Episode,E, · ]$INFO[Container(301).ListItem.Title]</label>\n                    </control>\n                    <control type="textbox">\n                        <height>143</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>143</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9345).NumPages,1) + !String.IsEqual(Container(9344).NumPages,1)</visible>\n                <top>25</top>\n                <height>232</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="label">\n                        <height>44</height>\n                        <font>font_main_bold</font>\n                        <textcolor>main_fg_100</textcolor>\n                        <label>$INFO[Container(301).ListItem.Season,S,]$INFO[Container(301).ListItem.Episode,E, · ]$INFO[Container(301).ListItem.Title]</label>\n                    </control>\n                    <control type="textbox">\n                        <height>178</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>178</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9346).NumPages,1) + !String.IsEqual(Container(9345).NumPages,1)</visible>\n                <top>8</top>\n                <height>267</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="label">\n                        <height>44</height>\n                        <font>font_main_bold</font>\n                        <textcolor>main_fg_100</textcolor>\n                        <label>$INFO[Container(301).ListItem.Season,S,]$INFO[Container(301).ListItem.Episode,E, · ]$INFO[Container(301).ListItem.Title]</label>\n                    </control>\n                    <control type="textbox">\n                        <height>213</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>213</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9347).NumPages,1) + !String.IsEqual(Container(9346).NumPages,1)</visible>\n                <top>0</top>\n                <height>283</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="label">\n                        <height>44</height>\n                        <font>font_main_bold</font>\n                        <textcolor>main_fg_100</textcolor>\n                        <label>$INFO[Container(301).ListItem.Season,S,]$INFO[Container(301).ListItem.Episode,E, · ]$INFO[Container(301).ListItem.Title]</label>\n                    </control>\n                    <control type="textbox">\n                        <height>229</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <autoscroll delay="8000" time="3000" repeat="10000">true</autoscroll>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>229</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <autoscroll delay="8000" time="3000" repeat="10000">true</autoscroll>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container(301).ListItem.DBType,episode) + !String.IsEqual(Container(9347).NumPages,1)</visible>\n                <top>0</top>\n                <height>283</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="label">\n                        <height>44</height>\n                        <font>font_main_bold</font>\n                        <textcolor>main_fg_100</textcolor>\n                        <label>$INFO[Container(301).ListItem.Season,S,]$INFO[Container(301).ListItem.Episode,E, · ]$INFO[Container(301).ListItem.Title]</label>\n                    </control>\n                    <control type="textbox">\n                        <height>229</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <autoscroll delay="8000" time="3000" repeat="10000">true</autoscroll>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>229</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <autoscroll delay="8000" time="3000" repeat="10000">true</autoscroll>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n        </control>\n',
        'already_patched_check': '<!-- ABUKARIM: plot box 4.6.21 (Spotlight): glass inside the page margin, centred on the info column -->',
        'description': 'AF3 Plot on the Right - Spotlight box centred (upgrade from 4.6.18)',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes_Hubs.xml'),
        'not_found_ok': True,
        'old': '        <!-- ABUKARIM: plot on the right -->\n        <control type="group">\n            <visible>Skin.HasSetting(abk.plotright) + !$EXP[Exp_Hubs_SlideInfo] + !$EXP[Exp_InfoDialogs] + !$EXP[Hub_Spotlight_Visible_Expression] + Integer.IsEqual(Window.Property(TMDBHelper.WidgetContainer),$PARAM[id]) + !String.IsEmpty(Container($PARAM[id]).ListItem.Plot)</visible>\n            <include>Home_Info_Animation</include>\n            <right>view_pad</right>\n            <width>700</width>\n            <top>200</top>\n            <height>300</height>\n            <!-- ABUKARIM: plot box fits the plot (4.6.18) -->\n            <!-- probes: invisible copies of the plot; Container(id).NumPages = 1 when it fits that height -->\n            <control type="textbox" id="9$PARAM[id]1">\n                <width>700</width>\n                <height>40</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n            </control>\n            <control type="textbox" id="9$PARAM[id]2">\n                <width>700</width>\n                <height>76</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n            </control>\n            <control type="textbox" id="9$PARAM[id]3">\n                <width>700</width>\n                <height>112</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n            </control>\n            <control type="textbox" id="9$PARAM[id]4">\n                <width>700</width>\n                <height>148</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n            </control>\n            <control type="textbox" id="9$PARAM[id]5">\n                <width>700</width>\n                <height>184</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n            </control>\n            <control type="textbox" id="9$PARAM[id]6">\n                <width>700</width>\n                <height>220</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n            </control>\n            <control type="textbox" id="9$PARAM[id]7">\n                <width>700</width>\n                <height>256</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n            </control>\n            <control type="textbox" id="9$PARAM[id]8">\n                <width>700</width>\n                <height>292</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(9$PARAM[id]1).NumPages,1)</visible>\n                <height>40</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-22</top>\n                    <right>-40</right>\n                    <bottom>-22</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-22</top>\n                    <right>-40</right>\n                    <bottom>-22</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(9$PARAM[id]2).NumPages,1) + !String.IsEqual(Container(9$PARAM[id]1).NumPages,1)</visible>\n                <height>76</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-22</top>\n                    <right>-40</right>\n                    <bottom>-22</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-22</top>\n                    <right>-40</right>\n                    <bottom>-22</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(9$PARAM[id]3).NumPages,1) + !String.IsEqual(Container(9$PARAM[id]2).NumPages,1)</visible>\n                <height>112</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-22</top>\n                    <right>-40</right>\n                    <bottom>-22</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-22</top>\n                    <right>-40</right>\n                    <bottom>-22</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(9$PARAM[id]4).NumPages,1) + !String.IsEqual(Container(9$PARAM[id]3).NumPages,1)</visible>\n                <height>148</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-22</top>\n                    <right>-40</right>\n                    <bottom>-22</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-22</top>\n                    <right>-40</right>\n                    <bottom>-22</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(9$PARAM[id]5).NumPages,1) + !String.IsEqual(Container(9$PARAM[id]4).NumPages,1)</visible>\n                <height>184</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-22</top>\n                    <right>-40</right>\n                    <bottom>-22</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-22</top>\n                    <right>-40</right>\n                    <bottom>-22</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(9$PARAM[id]6).NumPages,1) + !String.IsEqual(Container(9$PARAM[id]5).NumPages,1)</visible>\n                <height>220</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-22</top>\n                    <right>-40</right>\n                    <bottom>-22</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-22</top>\n                    <right>-40</right>\n                    <bottom>-22</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(9$PARAM[id]7).NumPages,1) + !String.IsEqual(Container(9$PARAM[id]6).NumPages,1)</visible>\n                <height>256</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-22</top>\n                    <right>-40</right>\n                    <bottom>-22</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-22</top>\n                    <right>-40</right>\n                    <bottom>-22</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(9$PARAM[id]8).NumPages,1) + !String.IsEqual(Container(9$PARAM[id]7).NumPages,1)</visible>\n                <height>292</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-22</top>\n                    <right>-40</right>\n                    <bottom>-22</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-22</top>\n                    <right>-40</right>\n                    <bottom>-22</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + !String.IsEqual(Container(9$PARAM[id]8).NumPages,1)</visible>\n                <height>300</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-22</top>\n                    <right>-40</right>\n                    <bottom>-22</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-22</top>\n                    <right>-40</right>\n                    <bottom>-22</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(9$PARAM[id]1).NumPages,1)</visible>\n                <height>94</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-22</top>\n                    <right>-40</right>\n                    <bottom>-22</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-22</top>\n                    <right>-40</right>\n                    <bottom>-22</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(9$PARAM[id]2).NumPages,1) + !String.IsEqual(Container(9$PARAM[id]1).NumPages,1)</visible>\n                <height>130</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-22</top>\n                    <right>-40</right>\n                    <bottom>-22</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-22</top>\n                    <right>-40</right>\n                    <bottom>-22</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(9$PARAM[id]3).NumPages,1) + !String.IsEqual(Container(9$PARAM[id]2).NumPages,1)</visible>\n                <height>166</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-22</top>\n                    <right>-40</right>\n                    <bottom>-22</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-22</top>\n                    <right>-40</right>\n                    <bottom>-22</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(9$PARAM[id]4).NumPages,1) + !String.IsEqual(Container(9$PARAM[id]3).NumPages,1)</visible>\n                <height>202</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-22</top>\n                    <right>-40</right>\n                    <bottom>-22</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-22</top>\n                    <right>-40</right>\n                    <bottom>-22</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(9$PARAM[id]5).NumPages,1) + !String.IsEqual(Container(9$PARAM[id]4).NumPages,1)</visible>\n                <height>238</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-22</top>\n                    <right>-40</right>\n                    <bottom>-22</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-22</top>\n                    <right>-40</right>\n                    <bottom>-22</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(9$PARAM[id]6).NumPages,1) + !String.IsEqual(Container(9$PARAM[id]5).NumPages,1)</visible>\n                <height>274</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-22</top>\n                    <right>-40</right>\n                    <bottom>-22</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-22</top>\n                    <right>-40</right>\n                    <bottom>-22</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(9$PARAM[id]7).NumPages,1) + !String.IsEqual(Container(9$PARAM[id]6).NumPages,1)</visible>\n                <height>300</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-22</top>\n                    <right>-40</right>\n                    <bottom>-22</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-22</top>\n                    <right>-40</right>\n                    <bottom>-22</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(9$PARAM[id]8).NumPages,1) + !String.IsEqual(Container(9$PARAM[id]7).NumPages,1)</visible>\n                <height>300</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-22</top>\n                    <right>-40</right>\n                    <bottom>-22</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-22</top>\n                    <right>-40</right>\n                    <bottom>-22</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + !String.IsEqual(Container(9$PARAM[id]8).NumPages,1)</visible>\n                <height>300</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-22</top>\n                    <right>-40</right>\n                    <bottom>-22</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-22</top>\n                    <right>-40</right>\n                    <bottom>-22</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n            </control>\n            <control type="grouplist">\n                <orientation>vertical</orientation>\n                <itemgap>10</itemgap>\n                <control type="label">\n                    <height>44</height>\n                    <font>font_main_bold</font>\n                    <textcolor>main_fg_100</textcolor>\n                    <label>$INFO[Container($PARAM[id]).ListItem.Season,S,]$INFO[Container($PARAM[id]).ListItem.Episode,E, · ]$INFO[Container($PARAM[id]).ListItem.Title]</label>\n                    <visible>String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode)</visible>\n                </control>\n                <control type="textbox">\n                    <height>300</height>\n                    <font>font_mini_plot</font>\n                    <textcolor>main_fg_90</textcolor>\n                    <align>right</align>\n                    <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                    <autoscroll delay="8000" time="3000" repeat="10000">true</autoscroll>\n                    <visible>String.StartsWith(System.Language,Arabic) + !String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode)</visible>\n                </control>\n                <control type="textbox">\n                    <height>246</height>\n                    <font>font_mini_plot</font>\n                    <textcolor>main_fg_90</textcolor>\n                    <align>right</align>\n                    <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                    <autoscroll delay="8000" time="3000" repeat="10000">true</autoscroll>\n                    <visible>String.StartsWith(System.Language,Arabic) + String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode)</visible>\n                </control>\n                <control type="textbox">\n                    <height>300</height>\n                    <font>font_mini_plot</font>\n                    <textcolor>main_fg_90</textcolor>\n                    <align>left</align>\n                    <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                    <autoscroll delay="8000" time="3000" repeat="10000">true</autoscroll>\n                    <visible>!String.StartsWith(System.Language,Arabic) + !String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode)</visible>\n                </control>\n                <control type="textbox">\n                    <height>246</height>\n                    <font>font_mini_plot</font>\n                    <textcolor>main_fg_90</textcolor>\n                    <align>left</align>\n                    <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                    <autoscroll delay="8000" time="3000" repeat="10000">true</autoscroll>\n                    <visible>!String.StartsWith(System.Language,Arabic) + String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode)</visible>\n                </control>\n            </control>\n        </control>\n',
        'new': '        <!-- ABUKARIM: plot on the right -->\n        <control type="group">\n            <visible>Skin.HasSetting(abk.plotright) + !$EXP[Exp_Hubs_SlideInfo] + !$EXP[Exp_InfoDialogs] + !$EXP[Hub_Spotlight_Visible_Expression] + Integer.IsEqual(Window.Property(TMDBHelper.WidgetContainer),$PARAM[id]) + !String.IsEmpty(Container($PARAM[id]).ListItem.Plot)</visible>\n            <include>Home_Info_Animation</include>\n            <right>120</right>\n            <width>700</width>\n            <top>179</top>\n            <height>283</height>\n            <!-- ABUKARIM: plot box 4.6.21 (hub info): glass inside the page margin, centred on the info column -->\n            <!-- probes: invisible copies of the plot, one per line count (line = 35 px);\n                 Container(id).NumPages = 1 when the plot fits that height -->\n            <control type="textbox" id="93$PARAM[id]1">\n                <width>700</width>\n                <height>38</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n            </control>\n            <control type="textbox" id="93$PARAM[id]2">\n                <width>700</width>\n                <height>73</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n            </control>\n            <control type="textbox" id="93$PARAM[id]3">\n                <width>700</width>\n                <height>108</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n            </control>\n            <control type="textbox" id="93$PARAM[id]4">\n                <width>700</width>\n                <height>143</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n            </control>\n            <control type="textbox" id="93$PARAM[id]5">\n                <width>700</width>\n                <height>178</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n            </control>\n            <control type="textbox" id="93$PARAM[id]6">\n                <width>700</width>\n                <height>213</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n            </control>\n            <control type="textbox" id="93$PARAM[id]7">\n                <width>700</width>\n                <height>248</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n            </control>\n            <!-- the box: the smallest height that holds the plot, centred on the info column -->\n            <control type="group">\n                <visible>!String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(93$PARAM[id]1).NumPages,1)</visible>\n                <top>122</top>\n                <height>38</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="textbox">\n                        <height>38</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>38</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(93$PARAM[id]2).NumPages,1) + !String.IsEqual(Container(93$PARAM[id]1).NumPages,1)</visible>\n                <top>105</top>\n                <height>73</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="textbox">\n                        <height>73</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>73</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(93$PARAM[id]3).NumPages,1) + !String.IsEqual(Container(93$PARAM[id]2).NumPages,1)</visible>\n                <top>87</top>\n                <height>108</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="textbox">\n                        <height>108</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>108</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(93$PARAM[id]4).NumPages,1) + !String.IsEqual(Container(93$PARAM[id]3).NumPages,1)</visible>\n                <top>70</top>\n                <height>143</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="textbox">\n                        <height>143</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>143</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(93$PARAM[id]5).NumPages,1) + !String.IsEqual(Container(93$PARAM[id]4).NumPages,1)</visible>\n                <top>52</top>\n                <height>178</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="textbox">\n                        <height>178</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>178</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(93$PARAM[id]6).NumPages,1) + !String.IsEqual(Container(93$PARAM[id]5).NumPages,1)</visible>\n                <top>35</top>\n                <height>213</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="textbox">\n                        <height>213</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>213</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(93$PARAM[id]7).NumPages,1) + !String.IsEqual(Container(93$PARAM[id]6).NumPages,1)</visible>\n                <top>17</top>\n                <height>248</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="textbox">\n                        <height>248</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>248</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + !String.IsEqual(Container(93$PARAM[id]7).NumPages,1)</visible>\n                <top>0</top>\n                <height>283</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="textbox">\n                        <height>283</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <autoscroll delay="8000" time="3000" repeat="10000">true</autoscroll>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>283</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <autoscroll delay="8000" time="3000" repeat="10000">true</autoscroll>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(93$PARAM[id]1).NumPages,1)</visible>\n                <top>95</top>\n                <height>92</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="label">\n                        <height>44</height>\n                        <font>font_main_bold</font>\n                        <textcolor>main_fg_100</textcolor>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Season,S,]$INFO[Container($PARAM[id]).ListItem.Episode,E, · ]$INFO[Container($PARAM[id]).ListItem.Title]</label>\n                    </control>\n                    <control type="textbox">\n                        <height>38</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>38</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(93$PARAM[id]2).NumPages,1) + !String.IsEqual(Container(93$PARAM[id]1).NumPages,1)</visible>\n                <top>78</top>\n                <height>127</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="label">\n                        <height>44</height>\n                        <font>font_main_bold</font>\n                        <textcolor>main_fg_100</textcolor>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Season,S,]$INFO[Container($PARAM[id]).ListItem.Episode,E, · ]$INFO[Container($PARAM[id]).ListItem.Title]</label>\n                    </control>\n                    <control type="textbox">\n                        <height>73</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>73</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(93$PARAM[id]3).NumPages,1) + !String.IsEqual(Container(93$PARAM[id]2).NumPages,1)</visible>\n                <top>60</top>\n                <height>162</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="label">\n                        <height>44</height>\n                        <font>font_main_bold</font>\n                        <textcolor>main_fg_100</textcolor>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Season,S,]$INFO[Container($PARAM[id]).ListItem.Episode,E, · ]$INFO[Container($PARAM[id]).ListItem.Title]</label>\n                    </control>\n                    <control type="textbox">\n                        <height>108</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>108</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(93$PARAM[id]4).NumPages,1) + !String.IsEqual(Container(93$PARAM[id]3).NumPages,1)</visible>\n                <top>43</top>\n                <height>197</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="label">\n                        <height>44</height>\n                        <font>font_main_bold</font>\n                        <textcolor>main_fg_100</textcolor>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Season,S,]$INFO[Container($PARAM[id]).ListItem.Episode,E, · ]$INFO[Container($PARAM[id]).ListItem.Title]</label>\n                    </control>\n                    <control type="textbox">\n                        <height>143</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>143</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(93$PARAM[id]5).NumPages,1) + !String.IsEqual(Container(93$PARAM[id]4).NumPages,1)</visible>\n                <top>25</top>\n                <height>232</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="label">\n                        <height>44</height>\n                        <font>font_main_bold</font>\n                        <textcolor>main_fg_100</textcolor>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Season,S,]$INFO[Container($PARAM[id]).ListItem.Episode,E, · ]$INFO[Container($PARAM[id]).ListItem.Title]</label>\n                    </control>\n                    <control type="textbox">\n                        <height>178</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>178</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(93$PARAM[id]6).NumPages,1) + !String.IsEqual(Container(93$PARAM[id]5).NumPages,1)</visible>\n                <top>8</top>\n                <height>267</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="label">\n                        <height>44</height>\n                        <font>font_main_bold</font>\n                        <textcolor>main_fg_100</textcolor>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Season,S,]$INFO[Container($PARAM[id]).ListItem.Episode,E, · ]$INFO[Container($PARAM[id]).ListItem.Title]</label>\n                    </control>\n                    <control type="textbox">\n                        <height>213</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>213</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(93$PARAM[id]7).NumPages,1) + !String.IsEqual(Container(93$PARAM[id]6).NumPages,1)</visible>\n                <top>0</top>\n                <height>283</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="label">\n                        <height>44</height>\n                        <font>font_main_bold</font>\n                        <textcolor>main_fg_100</textcolor>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Season,S,]$INFO[Container($PARAM[id]).ListItem.Episode,E, · ]$INFO[Container($PARAM[id]).ListItem.Title]</label>\n                    </control>\n                    <control type="textbox">\n                        <height>229</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <autoscroll delay="8000" time="3000" repeat="10000">true</autoscroll>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>229</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <autoscroll delay="8000" time="3000" repeat="10000">true</autoscroll>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + !String.IsEqual(Container(93$PARAM[id]7).NumPages,1)</visible>\n                <top>0</top>\n                <height>283</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="label">\n                        <height>44</height>\n                        <font>font_main_bold</font>\n                        <textcolor>main_fg_100</textcolor>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Season,S,]$INFO[Container($PARAM[id]).ListItem.Episode,E, · ]$INFO[Container($PARAM[id]).ListItem.Title]</label>\n                    </control>\n                    <control type="textbox">\n                        <height>229</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <autoscroll delay="8000" time="3000" repeat="10000">true</autoscroll>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>229</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <autoscroll delay="8000" time="3000" repeat="10000">true</autoscroll>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n        </control>\n',
        'already_patched_check': '<!-- ABUKARIM: plot box 4.6.21 (hub info): glass inside the page margin, centred on the info column -->',
        'description': 'AF3 Plot on the Right - hub info box centred (upgrade from 4.6.18)',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes_Info.xml'),
        'not_found_ok': True,
        'old': '                    <visible>$PARAM[plotright_genre] + !String.IsEmpty($PARAM[container]$PARAM[listitem].Genre)</visible>\n                    <height>54</height>\n                    <control type="label">\n                        <left>40</left>\n                        <top>4</top>\n',
        'new': '                    <visible>$PARAM[plotright_genre] + !String.IsEmpty($PARAM[container]$PARAM[listitem].Genre)</visible>\n                    <height>24</height>\n                    <control type="label">\n                        <left>40</left>\n                        <top>-11</top>\n',
        'already_patched_check': '<top>-11</top>',
        'description': 'AF3 Plot on the Right - genre line rhythm (upgrade)',
    },

    # 4.6.19: AF3 writes "2 hours 0 minutes" for a running time of whole hours.
    # The hours + minutes label now hides when the minutes are 0 and an hours-
    # only label takes its place.
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes_Info.xml'),
        'not_found_ok': True,
        'old': '                    <include content="Info_Line_Label">\n                        <param name="colordiffuse">$PARAM[colordiffuse]</param>\n                        <param name="label">$INFO[$PARAM[container]$PARAM[listitem].Duration(h),, $LOCALIZE[31074] ]$INFO[$PARAM[container]$PARAM[listitem].Duration(m),, $LOCALIZE[31073]]</param>\n                        <param name="visible">!String.IsEmpty($PARAM[container]$PARAM[listitem].Duration) + !Integer.IsEqual($PARAM[container]$PARAM[listitem].Duration(h),0) + [String.IsEqual($PARAM[container]$PARAM[listitem].DBType,movie) | String.IsEqual($PARAM[container]$PARAM[listitem].DBType,tvshow) | String.IsEqual($PARAM[container]$PARAM[listitem].DBType,episode) | String.IsEqual($PARAM[container]$PARAM[listitem].DBType,season) | String.IsEqual($PARAM[container]$PARAM[listitem].DBType,video) | $PARAM[override]]</param>\n                    </include>\n',
        'new': '                    <!-- ABUKARIM: whole hours -->\n                    <include content="Info_Line_Label">\n                        <param name="colordiffuse">$PARAM[colordiffuse]</param>\n                        <param name="label">$INFO[$PARAM[container]$PARAM[listitem].Duration(h),, $LOCALIZE[31074]]</param>\n                        <param name="visible">!String.IsEmpty($PARAM[container]$PARAM[listitem].Duration) + !Integer.IsEqual($PARAM[container]$PARAM[listitem].Duration(h),0) + Integer.IsEqual($PARAM[container]$PARAM[listitem].Duration(m),0) + [String.IsEqual($PARAM[container]$PARAM[listitem].DBType,movie) | String.IsEqual($PARAM[container]$PARAM[listitem].DBType,tvshow) | String.IsEqual($PARAM[container]$PARAM[listitem].DBType,episode) | String.IsEqual($PARAM[container]$PARAM[listitem].DBType,season) | String.IsEqual($PARAM[container]$PARAM[listitem].DBType,video) | $PARAM[override]]</param>\n                    </include>\n                    <include content="Info_Line_Label">\n                        <param name="colordiffuse">$PARAM[colordiffuse]</param>\n                        <param name="label">$INFO[$PARAM[container]$PARAM[listitem].Duration(h),, $LOCALIZE[31074] ]$INFO[$PARAM[container]$PARAM[listitem].Duration(m),, $LOCALIZE[31073]]</param>\n                        <param name="visible">!String.IsEmpty($PARAM[container]$PARAM[listitem].Duration) + !Integer.IsEqual($PARAM[container]$PARAM[listitem].Duration(h),0) + !Integer.IsEqual($PARAM[container]$PARAM[listitem].Duration(m),0) + [String.IsEqual($PARAM[container]$PARAM[listitem].DBType,movie) | String.IsEqual($PARAM[container]$PARAM[listitem].DBType,tvshow) | String.IsEqual($PARAM[container]$PARAM[listitem].DBType,episode) | String.IsEqual($PARAM[container]$PARAM[listitem].DBType,season) | String.IsEqual($PARAM[container]$PARAM[listitem].DBType,video) | $PARAM[override]]</param>\n                    </include>\n',
        'already_patched_check': '<!-- ABUKARIM: whole hours -->',
        'description': 'AF3 - info line: whole hours without "0 minutes" (one-row)',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes_u3k.xml'),
        'not_found_ok': True,
        'old': '                    <include content="Info_Line_Label">\n                        <param name="colordiffuse">$PARAM[colordiffuse]</param>\n                        <param name="label">$INFO[$PARAM[container]$PARAM[listitem].Duration(h),, $LOCALIZE[31074] ]$INFO[$PARAM[container]$PARAM[listitem].Duration(m),, $LOCALIZE[31073]]</param>\n                        <param name="visible">!String.IsEmpty($PARAM[container]$PARAM[listitem].Duration) + !Integer.IsEqual($PARAM[container]$PARAM[listitem].Duration(h),0) + [String.IsEqual($PARAM[container]$PARAM[listitem].DBType,movie) | String.IsEqual($PARAM[container]$PARAM[listitem].DBType,tvshow) | String.IsEqual($PARAM[container]$PARAM[listitem].DBType,episode) | String.IsEqual($PARAM[container]$PARAM[listitem].DBType,season) | $PARAM[override]]</param>\n                    </include>\n',
        'new': '                    <!-- ABUKARIM: whole hours -->\n                    <include content="Info_Line_Label">\n                        <param name="colordiffuse">$PARAM[colordiffuse]</param>\n                        <param name="label">$INFO[$PARAM[container]$PARAM[listitem].Duration(h),, $LOCALIZE[31074]]</param>\n                        <param name="visible">!String.IsEmpty($PARAM[container]$PARAM[listitem].Duration) + !Integer.IsEqual($PARAM[container]$PARAM[listitem].Duration(h),0) + Integer.IsEqual($PARAM[container]$PARAM[listitem].Duration(m),0) + [String.IsEqual($PARAM[container]$PARAM[listitem].DBType,movie) | String.IsEqual($PARAM[container]$PARAM[listitem].DBType,tvshow) | String.IsEqual($PARAM[container]$PARAM[listitem].DBType,episode) | String.IsEqual($PARAM[container]$PARAM[listitem].DBType,season) | $PARAM[override]]</param>\n                    </include>\n                    <include content="Info_Line_Label">\n                        <param name="colordiffuse">$PARAM[colordiffuse]</param>\n                        <param name="label">$INFO[$PARAM[container]$PARAM[listitem].Duration(h),, $LOCALIZE[31074] ]$INFO[$PARAM[container]$PARAM[listitem].Duration(m),, $LOCALIZE[31073]]</param>\n                        <param name="visible">!String.IsEmpty($PARAM[container]$PARAM[listitem].Duration) + !Integer.IsEqual($PARAM[container]$PARAM[listitem].Duration(h),0) + !Integer.IsEqual($PARAM[container]$PARAM[listitem].Duration(m),0) + [String.IsEqual($PARAM[container]$PARAM[listitem].DBType,movie) | String.IsEqual($PARAM[container]$PARAM[listitem].DBType,tvshow) | String.IsEqual($PARAM[container]$PARAM[listitem].DBType,episode) | String.IsEqual($PARAM[container]$PARAM[listitem].DBType,season) | $PARAM[override]]</param>\n                    </include>\n',
        'already_patched_check': '<!-- ABUKARIM: whole hours -->',
        'description': 'AF3 - info line: whole hours without "0 minutes" (two-row)',
    },

    # 4.6.19: in AF3's two-line information bar the stars open the second row,
    # so their leading dot hung alone at the start of the line. The star
    # rating include gets a divider param (default true - unchanged elsewhere)
    # and the two-line bar passes false.
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes_Info.xml'),
        'not_found_ok': True,
        'old': '    <include name="Info_Line_StarRating">\n        <param name="visible">true</param>\n        <definition>\n            <include content="Info_Line_Divider">\n                <param name="visible">$PARAM[visible] + !Skin.HasSetting(Info.EnablePillboxStyle)</param>',
        'new': '    <include name="Info_Line_StarRating">\n        <param name="visible">true</param>\n        <param name="divider">true</param>  <!-- ABUKARIM: no leading dot when the stars open a row -->\n        <definition>\n            <include content="Info_Line_Divider">\n                <param name="visible">$PARAM[visible] + $PARAM[divider] + !Skin.HasSetting(Info.EnablePillboxStyle)</param>',
        'already_patched_check': '<param name="divider">true</param>  <!-- ABUKARIM',
        'description': 'AF3 - star rating: divider param',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes_u3k.xml'),
        'not_found_ok': True,
        'old': '                        <param name="rating">$PARAM[container]$PARAM[listitem].Rating</param>\n',
        'new': '                        <param name="rating">$PARAM[container]$PARAM[listitem].Rating</param>\n                        <param name="divider">false</param>  <!-- ABUKARIM: stars open the row -->\n',
        'already_patched_check': '                        <param name="rating">$PARAM[container]$PARAM[listitem].Rating</param>\n                        <param name="divider">false</param>  <!-- ABUKARIM: stars open the row -->\n',
        'description': 'AF3 - two-line info bar: no leading dot before the stars (Rating)',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes_u3k.xml'),
        'not_found_ok': True,
        'old': '                        <param name="rating">$PARAM[container]$PARAM[listitem].UserRating</param>\n',
        'new': '                        <param name="rating">$PARAM[container]$PARAM[listitem].UserRating</param>\n                        <param name="divider">false</param>  <!-- ABUKARIM: stars open the row -->\n',
        'already_patched_check': '                        <param name="rating">$PARAM[container]$PARAM[listitem].UserRating</param>\n                        <param name="divider">false</param>  <!-- ABUKARIM: stars open the row -->\n',
        'description': 'AF3 - two-line info bar: no leading dot before the stars (UserRating)',
    },

    # 4.6.21 (screenshot 2026-10-31 08:09): no empty band under the info
    # column - with the plot on the right the column (logo .. ratings) moves
    # down 64 px so it ends one gap above the row title; the glass keeps
    # inside the page margin (right edge 80 px from the screen edge, like the
    # left text) and is centred on the column again.
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes_Hubs.xml'),
        'not_found_ok': True,
        'old': '        <!-- ABUKARIM: plot on the right -->\n        <control type="group">\n            <visible>Skin.HasSetting(abk.plotright) + !$EXP[Exp_InfoDialogs] + $EXP[Hub_Spotlight_Visible_Expression] + String.IsEmpty(Window(Home).Property(Background.ShowOverlay)) + !String.IsEmpty(Container(301).ListItem.Plot)</visible>\n            <animation effect="slide" end="0" start="0,-200" time="400" tween="cubic" easing="out" reversible="false" condition="!Control.HasFocus(300)">Visible</animation>\n            <animation effect="slide" start="0" end="0,-200" time="400" tween="cubic" easing="out" reversible="false">Hidden</animation>\n            <right>view_pad</right>\n            <width>700</width>\n            <top>194</top>\n            <height>283</height>\n            <!-- ABUKARIM: plot box centred on the info, fits the plot (4.6.19) -->\n            <!-- probes: invisible copies of the plot, one per line count (line = 35 px);\n                 Container(id).NumPages = 1 when the plot fits that height -->\n            <control type="textbox" id="9341">\n                <width>700</width>\n                <height>38</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container(301).ListItem.Plot]</label>\n            </control>\n            <control type="textbox" id="9342">\n                <width>700</width>\n                <height>73</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container(301).ListItem.Plot]</label>\n            </control>\n            <control type="textbox" id="9343">\n                <width>700</width>\n                <height>108</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container(301).ListItem.Plot]</label>\n            </control>\n            <control type="textbox" id="9344">\n                <width>700</width>\n                <height>143</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container(301).ListItem.Plot]</label>\n            </control>\n            <control type="textbox" id="9345">\n                <width>700</width>\n                <height>178</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container(301).ListItem.Plot]</label>\n            </control>\n            <control type="textbox" id="9346">\n                <width>700</width>\n                <height>213</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container(301).ListItem.Plot]</label>\n            </control>\n            <control type="textbox" id="9347">\n                <width>700</width>\n                <height>248</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container(301).ListItem.Plot]</label>\n            </control>\n            <!-- the box: the smallest height that holds the plot, centred on the info column -->\n            <control type="group">\n                <visible>!String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9341).NumPages,1)</visible>\n                <top>122</top>\n                <height>38</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="textbox">\n                        <height>38</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>38</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9342).NumPages,1) + !String.IsEqual(Container(9341).NumPages,1)</visible>\n                <top>105</top>\n                <height>73</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="textbox">\n                        <height>73</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>73</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9343).NumPages,1) + !String.IsEqual(Container(9342).NumPages,1)</visible>\n                <top>87</top>\n                <height>108</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="textbox">\n                        <height>108</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>108</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9344).NumPages,1) + !String.IsEqual(Container(9343).NumPages,1)</visible>\n                <top>70</top>\n                <height>143</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="textbox">\n                        <height>143</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>143</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9345).NumPages,1) + !String.IsEqual(Container(9344).NumPages,1)</visible>\n                <top>52</top>\n                <height>178</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="textbox">\n                        <height>178</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>178</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9346).NumPages,1) + !String.IsEqual(Container(9345).NumPages,1)</visible>\n                <top>35</top>\n                <height>213</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="textbox">\n                        <height>213</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>213</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9347).NumPages,1) + !String.IsEqual(Container(9346).NumPages,1)</visible>\n                <top>17</top>\n                <height>248</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="textbox">\n                        <height>248</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>248</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container(301).ListItem.DBType,episode) + !String.IsEqual(Container(9347).NumPages,1)</visible>\n                <top>0</top>\n                <height>283</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="textbox">\n                        <height>283</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <autoscroll delay="8000" time="3000" repeat="10000">true</autoscroll>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>283</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <autoscroll delay="8000" time="3000" repeat="10000">true</autoscroll>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9341).NumPages,1)</visible>\n                <top>95</top>\n                <height>92</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="label">\n                        <height>44</height>\n                        <font>font_main_bold</font>\n                        <textcolor>main_fg_100</textcolor>\n                        <label>$INFO[Container(301).ListItem.Season,S,]$INFO[Container(301).ListItem.Episode,E, · ]$INFO[Container(301).ListItem.Title]</label>\n                    </control>\n                    <control type="textbox">\n                        <height>38</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>38</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9342).NumPages,1) + !String.IsEqual(Container(9341).NumPages,1)</visible>\n                <top>78</top>\n                <height>127</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="label">\n                        <height>44</height>\n                        <font>font_main_bold</font>\n                        <textcolor>main_fg_100</textcolor>\n                        <label>$INFO[Container(301).ListItem.Season,S,]$INFO[Container(301).ListItem.Episode,E, · ]$INFO[Container(301).ListItem.Title]</label>\n                    </control>\n                    <control type="textbox">\n                        <height>73</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>73</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9343).NumPages,1) + !String.IsEqual(Container(9342).NumPages,1)</visible>\n                <top>60</top>\n                <height>162</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="label">\n                        <height>44</height>\n                        <font>font_main_bold</font>\n                        <textcolor>main_fg_100</textcolor>\n                        <label>$INFO[Container(301).ListItem.Season,S,]$INFO[Container(301).ListItem.Episode,E, · ]$INFO[Container(301).ListItem.Title]</label>\n                    </control>\n                    <control type="textbox">\n                        <height>108</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>108</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9344).NumPages,1) + !String.IsEqual(Container(9343).NumPages,1)</visible>\n                <top>43</top>\n                <height>197</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="label">\n                        <height>44</height>\n                        <font>font_main_bold</font>\n                        <textcolor>main_fg_100</textcolor>\n                        <label>$INFO[Container(301).ListItem.Season,S,]$INFO[Container(301).ListItem.Episode,E, · ]$INFO[Container(301).ListItem.Title]</label>\n                    </control>\n                    <control type="textbox">\n                        <height>143</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>143</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9345).NumPages,1) + !String.IsEqual(Container(9344).NumPages,1)</visible>\n                <top>25</top>\n                <height>232</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="label">\n                        <height>44</height>\n                        <font>font_main_bold</font>\n                        <textcolor>main_fg_100</textcolor>\n                        <label>$INFO[Container(301).ListItem.Season,S,]$INFO[Container(301).ListItem.Episode,E, · ]$INFO[Container(301).ListItem.Title]</label>\n                    </control>\n                    <control type="textbox">\n                        <height>178</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>178</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9346).NumPages,1) + !String.IsEqual(Container(9345).NumPages,1)</visible>\n                <top>8</top>\n                <height>267</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="label">\n                        <height>44</height>\n                        <font>font_main_bold</font>\n                        <textcolor>main_fg_100</textcolor>\n                        <label>$INFO[Container(301).ListItem.Season,S,]$INFO[Container(301).ListItem.Episode,E, · ]$INFO[Container(301).ListItem.Title]</label>\n                    </control>\n                    <control type="textbox">\n                        <height>213</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>213</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9347).NumPages,1) + !String.IsEqual(Container(9346).NumPages,1)</visible>\n                <top>0</top>\n                <height>283</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="label">\n                        <height>44</height>\n                        <font>font_main_bold</font>\n                        <textcolor>main_fg_100</textcolor>\n                        <label>$INFO[Container(301).ListItem.Season,S,]$INFO[Container(301).ListItem.Episode,E, · ]$INFO[Container(301).ListItem.Title]</label>\n                    </control>\n                    <control type="textbox">\n                        <height>229</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <autoscroll delay="8000" time="3000" repeat="10000">true</autoscroll>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>229</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <autoscroll delay="8000" time="3000" repeat="10000">true</autoscroll>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container(301).ListItem.DBType,episode) + !String.IsEqual(Container(9347).NumPages,1)</visible>\n                <top>0</top>\n                <height>283</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="label">\n                        <height>44</height>\n                        <font>font_main_bold</font>\n                        <textcolor>main_fg_100</textcolor>\n                        <label>$INFO[Container(301).ListItem.Season,S,]$INFO[Container(301).ListItem.Episode,E, · ]$INFO[Container(301).ListItem.Title]</label>\n                    </control>\n                    <control type="textbox">\n                        <height>229</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <autoscroll delay="8000" time="3000" repeat="10000">true</autoscroll>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>229</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <autoscroll delay="8000" time="3000" repeat="10000">true</autoscroll>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n        </control>\n',
        'new': '        <!-- ABUKARIM: plot on the right -->\n        <control type="group">\n            <visible>Skin.HasSetting(abk.plotright) + !$EXP[Exp_InfoDialogs] + $EXP[Hub_Spotlight_Visible_Expression] + String.IsEmpty(Window(Home).Property(Background.ShowOverlay)) + !String.IsEmpty(Container(301).ListItem.Plot)</visible>\n            <animation effect="slide" end="0" start="0,-200" time="400" tween="cubic" easing="out" reversible="false" condition="!Control.HasFocus(300)">Visible</animation>\n            <animation effect="slide" start="0" end="0,-200" time="400" tween="cubic" easing="out" reversible="false">Hidden</animation>\n            <right>120</right>\n            <width>700</width>\n            <top>164</top>\n            <height>283</height>\n            <!-- ABUKARIM: plot box 4.6.21 (Spotlight): glass inside the page margin, centred on the info column -->\n            <!-- probes: invisible copies of the plot, one per line count (line = 35 px);\n                 Container(id).NumPages = 1 when the plot fits that height -->\n            <control type="textbox" id="9341">\n                <width>700</width>\n                <height>38</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container(301).ListItem.Plot]</label>\n            </control>\n            <control type="textbox" id="9342">\n                <width>700</width>\n                <height>73</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container(301).ListItem.Plot]</label>\n            </control>\n            <control type="textbox" id="9343">\n                <width>700</width>\n                <height>108</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container(301).ListItem.Plot]</label>\n            </control>\n            <control type="textbox" id="9344">\n                <width>700</width>\n                <height>143</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container(301).ListItem.Plot]</label>\n            </control>\n            <control type="textbox" id="9345">\n                <width>700</width>\n                <height>178</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container(301).ListItem.Plot]</label>\n            </control>\n            <control type="textbox" id="9346">\n                <width>700</width>\n                <height>213</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container(301).ListItem.Plot]</label>\n            </control>\n            <control type="textbox" id="9347">\n                <width>700</width>\n                <height>248</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container(301).ListItem.Plot]</label>\n            </control>\n            <!-- the box: the smallest height that holds the plot, centred on the info column -->\n            <control type="group">\n                <visible>!String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9341).NumPages,1)</visible>\n                <top>122</top>\n                <height>38</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="textbox">\n                        <height>38</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>38</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9342).NumPages,1) + !String.IsEqual(Container(9341).NumPages,1)</visible>\n                <top>105</top>\n                <height>73</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="textbox">\n                        <height>73</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>73</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9343).NumPages,1) + !String.IsEqual(Container(9342).NumPages,1)</visible>\n                <top>87</top>\n                <height>108</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="textbox">\n                        <height>108</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>108</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9344).NumPages,1) + !String.IsEqual(Container(9343).NumPages,1)</visible>\n                <top>70</top>\n                <height>143</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="textbox">\n                        <height>143</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>143</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9345).NumPages,1) + !String.IsEqual(Container(9344).NumPages,1)</visible>\n                <top>52</top>\n                <height>178</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="textbox">\n                        <height>178</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>178</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9346).NumPages,1) + !String.IsEqual(Container(9345).NumPages,1)</visible>\n                <top>35</top>\n                <height>213</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="textbox">\n                        <height>213</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>213</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9347).NumPages,1) + !String.IsEqual(Container(9346).NumPages,1)</visible>\n                <top>17</top>\n                <height>248</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="textbox">\n                        <height>248</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>248</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container(301).ListItem.DBType,episode) + !String.IsEqual(Container(9347).NumPages,1)</visible>\n                <top>0</top>\n                <height>283</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="textbox">\n                        <height>283</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <autoscroll delay="8000" time="3000" repeat="10000">true</autoscroll>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>283</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <autoscroll delay="8000" time="3000" repeat="10000">true</autoscroll>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9341).NumPages,1)</visible>\n                <top>95</top>\n                <height>92</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="label">\n                        <height>44</height>\n                        <font>font_main_bold</font>\n                        <textcolor>main_fg_100</textcolor>\n                        <label>$INFO[Container(301).ListItem.Season,S,]$INFO[Container(301).ListItem.Episode,E, · ]$INFO[Container(301).ListItem.Title]</label>\n                    </control>\n                    <control type="textbox">\n                        <height>38</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>38</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9342).NumPages,1) + !String.IsEqual(Container(9341).NumPages,1)</visible>\n                <top>78</top>\n                <height>127</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="label">\n                        <height>44</height>\n                        <font>font_main_bold</font>\n                        <textcolor>main_fg_100</textcolor>\n                        <label>$INFO[Container(301).ListItem.Season,S,]$INFO[Container(301).ListItem.Episode,E, · ]$INFO[Container(301).ListItem.Title]</label>\n                    </control>\n                    <control type="textbox">\n                        <height>73</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>73</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9343).NumPages,1) + !String.IsEqual(Container(9342).NumPages,1)</visible>\n                <top>60</top>\n                <height>162</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="label">\n                        <height>44</height>\n                        <font>font_main_bold</font>\n                        <textcolor>main_fg_100</textcolor>\n                        <label>$INFO[Container(301).ListItem.Season,S,]$INFO[Container(301).ListItem.Episode,E, · ]$INFO[Container(301).ListItem.Title]</label>\n                    </control>\n                    <control type="textbox">\n                        <height>108</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>108</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9344).NumPages,1) + !String.IsEqual(Container(9343).NumPages,1)</visible>\n                <top>43</top>\n                <height>197</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="label">\n                        <height>44</height>\n                        <font>font_main_bold</font>\n                        <textcolor>main_fg_100</textcolor>\n                        <label>$INFO[Container(301).ListItem.Season,S,]$INFO[Container(301).ListItem.Episode,E, · ]$INFO[Container(301).ListItem.Title]</label>\n                    </control>\n                    <control type="textbox">\n                        <height>143</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>143</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9345).NumPages,1) + !String.IsEqual(Container(9344).NumPages,1)</visible>\n                <top>25</top>\n                <height>232</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="label">\n                        <height>44</height>\n                        <font>font_main_bold</font>\n                        <textcolor>main_fg_100</textcolor>\n                        <label>$INFO[Container(301).ListItem.Season,S,]$INFO[Container(301).ListItem.Episode,E, · ]$INFO[Container(301).ListItem.Title]</label>\n                    </control>\n                    <control type="textbox">\n                        <height>178</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>178</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9346).NumPages,1) + !String.IsEqual(Container(9345).NumPages,1)</visible>\n                <top>8</top>\n                <height>267</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="label">\n                        <height>44</height>\n                        <font>font_main_bold</font>\n                        <textcolor>main_fg_100</textcolor>\n                        <label>$INFO[Container(301).ListItem.Season,S,]$INFO[Container(301).ListItem.Episode,E, · ]$INFO[Container(301).ListItem.Title]</label>\n                    </control>\n                    <control type="textbox">\n                        <height>213</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>213</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container(301).ListItem.DBType,episode) + String.IsEqual(Container(9347).NumPages,1) + !String.IsEqual(Container(9346).NumPages,1)</visible>\n                <top>0</top>\n                <height>283</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="label">\n                        <height>44</height>\n                        <font>font_main_bold</font>\n                        <textcolor>main_fg_100</textcolor>\n                        <label>$INFO[Container(301).ListItem.Season,S,]$INFO[Container(301).ListItem.Episode,E, · ]$INFO[Container(301).ListItem.Title]</label>\n                    </control>\n                    <control type="textbox">\n                        <height>229</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <autoscroll delay="8000" time="3000" repeat="10000">true</autoscroll>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>229</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <autoscroll delay="8000" time="3000" repeat="10000">true</autoscroll>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container(301).ListItem.DBType,episode) + !String.IsEqual(Container(9347).NumPages,1)</visible>\n                <top>0</top>\n                <height>283</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="label">\n                        <height>44</height>\n                        <font>font_main_bold</font>\n                        <textcolor>main_fg_100</textcolor>\n                        <label>$INFO[Container(301).ListItem.Season,S,]$INFO[Container(301).ListItem.Episode,E, · ]$INFO[Container(301).ListItem.Title]</label>\n                    </control>\n                    <control type="textbox">\n                        <height>229</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <autoscroll delay="8000" time="3000" repeat="10000">true</autoscroll>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>229</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container(301).ListItem.Plot]</label>\n                        <autoscroll delay="8000" time="3000" repeat="10000">true</autoscroll>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n        </control>\n',
        'already_patched_check': '<!-- ABUKARIM: plot box 4.6.21 (Spotlight): glass inside the page margin, centred on the info column -->',
        'description': 'AF3 Plot on the Right - Spotlight box margin (upgrade from 4.6.19)',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes_Hubs.xml'),
        'not_found_ok': True,
        'old': '        <!-- ABUKARIM: plot on the right -->\n        <control type="group">\n            <visible>Skin.HasSetting(abk.plotright) + !$EXP[Exp_Hubs_SlideInfo] + !$EXP[Exp_InfoDialogs] + !$EXP[Hub_Spotlight_Visible_Expression] + Integer.IsEqual(Window.Property(TMDBHelper.WidgetContainer),$PARAM[id]) + !String.IsEmpty(Container($PARAM[id]).ListItem.Plot)</visible>\n            <include>Home_Info_Animation</include>\n            <right>view_pad</right>\n            <width>700</width>\n            <top>209</top>\n            <height>283</height>\n            <!-- ABUKARIM: plot box centred on the info, fits the plot (4.6.19) -->\n            <!-- probes: invisible copies of the plot, one per line count (line = 35 px);\n                 Container(id).NumPages = 1 when the plot fits that height -->\n            <control type="textbox" id="93$PARAM[id]1">\n                <width>700</width>\n                <height>38</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n            </control>\n            <control type="textbox" id="93$PARAM[id]2">\n                <width>700</width>\n                <height>73</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n            </control>\n            <control type="textbox" id="93$PARAM[id]3">\n                <width>700</width>\n                <height>108</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n            </control>\n            <control type="textbox" id="93$PARAM[id]4">\n                <width>700</width>\n                <height>143</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n            </control>\n            <control type="textbox" id="93$PARAM[id]5">\n                <width>700</width>\n                <height>178</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n            </control>\n            <control type="textbox" id="93$PARAM[id]6">\n                <width>700</width>\n                <height>213</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n            </control>\n            <control type="textbox" id="93$PARAM[id]7">\n                <width>700</width>\n                <height>248</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n            </control>\n            <!-- the box: the smallest height that holds the plot, centred on the info column -->\n            <control type="group">\n                <visible>!String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(93$PARAM[id]1).NumPages,1)</visible>\n                <top>122</top>\n                <height>38</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="textbox">\n                        <height>38</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>38</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(93$PARAM[id]2).NumPages,1) + !String.IsEqual(Container(93$PARAM[id]1).NumPages,1)</visible>\n                <top>105</top>\n                <height>73</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="textbox">\n                        <height>73</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>73</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(93$PARAM[id]3).NumPages,1) + !String.IsEqual(Container(93$PARAM[id]2).NumPages,1)</visible>\n                <top>87</top>\n                <height>108</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="textbox">\n                        <height>108</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>108</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(93$PARAM[id]4).NumPages,1) + !String.IsEqual(Container(93$PARAM[id]3).NumPages,1)</visible>\n                <top>70</top>\n                <height>143</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="textbox">\n                        <height>143</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>143</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(93$PARAM[id]5).NumPages,1) + !String.IsEqual(Container(93$PARAM[id]4).NumPages,1)</visible>\n                <top>52</top>\n                <height>178</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="textbox">\n                        <height>178</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>178</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(93$PARAM[id]6).NumPages,1) + !String.IsEqual(Container(93$PARAM[id]5).NumPages,1)</visible>\n                <top>35</top>\n                <height>213</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="textbox">\n                        <height>213</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>213</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(93$PARAM[id]7).NumPages,1) + !String.IsEqual(Container(93$PARAM[id]6).NumPages,1)</visible>\n                <top>17</top>\n                <height>248</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="textbox">\n                        <height>248</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>248</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + !String.IsEqual(Container(93$PARAM[id]7).NumPages,1)</visible>\n                <top>0</top>\n                <height>283</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="textbox">\n                        <height>283</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <autoscroll delay="8000" time="3000" repeat="10000">true</autoscroll>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>283</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <autoscroll delay="8000" time="3000" repeat="10000">true</autoscroll>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(93$PARAM[id]1).NumPages,1)</visible>\n                <top>95</top>\n                <height>92</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="label">\n                        <height>44</height>\n                        <font>font_main_bold</font>\n                        <textcolor>main_fg_100</textcolor>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Season,S,]$INFO[Container($PARAM[id]).ListItem.Episode,E, · ]$INFO[Container($PARAM[id]).ListItem.Title]</label>\n                    </control>\n                    <control type="textbox">\n                        <height>38</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>38</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(93$PARAM[id]2).NumPages,1) + !String.IsEqual(Container(93$PARAM[id]1).NumPages,1)</visible>\n                <top>78</top>\n                <height>127</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="label">\n                        <height>44</height>\n                        <font>font_main_bold</font>\n                        <textcolor>main_fg_100</textcolor>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Season,S,]$INFO[Container($PARAM[id]).ListItem.Episode,E, · ]$INFO[Container($PARAM[id]).ListItem.Title]</label>\n                    </control>\n                    <control type="textbox">\n                        <height>73</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>73</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(93$PARAM[id]3).NumPages,1) + !String.IsEqual(Container(93$PARAM[id]2).NumPages,1)</visible>\n                <top>60</top>\n                <height>162</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="label">\n                        <height>44</height>\n                        <font>font_main_bold</font>\n                        <textcolor>main_fg_100</textcolor>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Season,S,]$INFO[Container($PARAM[id]).ListItem.Episode,E, · ]$INFO[Container($PARAM[id]).ListItem.Title]</label>\n                    </control>\n                    <control type="textbox">\n                        <height>108</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>108</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(93$PARAM[id]4).NumPages,1) + !String.IsEqual(Container(93$PARAM[id]3).NumPages,1)</visible>\n                <top>43</top>\n                <height>197</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="label">\n                        <height>44</height>\n                        <font>font_main_bold</font>\n                        <textcolor>main_fg_100</textcolor>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Season,S,]$INFO[Container($PARAM[id]).ListItem.Episode,E, · ]$INFO[Container($PARAM[id]).ListItem.Title]</label>\n                    </control>\n                    <control type="textbox">\n                        <height>143</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>143</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(93$PARAM[id]5).NumPages,1) + !String.IsEqual(Container(93$PARAM[id]4).NumPages,1)</visible>\n                <top>25</top>\n                <height>232</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="label">\n                        <height>44</height>\n                        <font>font_main_bold</font>\n                        <textcolor>main_fg_100</textcolor>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Season,S,]$INFO[Container($PARAM[id]).ListItem.Episode,E, · ]$INFO[Container($PARAM[id]).ListItem.Title]</label>\n                    </control>\n                    <control type="textbox">\n                        <height>178</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>178</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(93$PARAM[id]6).NumPages,1) + !String.IsEqual(Container(93$PARAM[id]5).NumPages,1)</visible>\n                <top>8</top>\n                <height>267</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="label">\n                        <height>44</height>\n                        <font>font_main_bold</font>\n                        <textcolor>main_fg_100</textcolor>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Season,S,]$INFO[Container($PARAM[id]).ListItem.Episode,E, · ]$INFO[Container($PARAM[id]).ListItem.Title]</label>\n                    </control>\n                    <control type="textbox">\n                        <height>213</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>213</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(93$PARAM[id]7).NumPages,1) + !String.IsEqual(Container(93$PARAM[id]6).NumPages,1)</visible>\n                <top>0</top>\n                <height>283</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="label">\n                        <height>44</height>\n                        <font>font_main_bold</font>\n                        <textcolor>main_fg_100</textcolor>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Season,S,]$INFO[Container($PARAM[id]).ListItem.Episode,E, · ]$INFO[Container($PARAM[id]).ListItem.Title]</label>\n                    </control>\n                    <control type="textbox">\n                        <height>229</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <autoscroll delay="8000" time="3000" repeat="10000">true</autoscroll>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>229</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <autoscroll delay="8000" time="3000" repeat="10000">true</autoscroll>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + !String.IsEqual(Container(93$PARAM[id]7).NumPages,1)</visible>\n                <top>0</top>\n                <height>283</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="label">\n                        <height>44</height>\n                        <font>font_main_bold</font>\n                        <textcolor>main_fg_100</textcolor>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Season,S,]$INFO[Container($PARAM[id]).ListItem.Episode,E, · ]$INFO[Container($PARAM[id]).ListItem.Title]</label>\n                    </control>\n                    <control type="textbox">\n                        <height>229</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <autoscroll delay="8000" time="3000" repeat="10000">true</autoscroll>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>229</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <autoscroll delay="8000" time="3000" repeat="10000">true</autoscroll>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n        </control>\n',
        'new': '        <!-- ABUKARIM: plot on the right -->\n        <control type="group">\n            <visible>Skin.HasSetting(abk.plotright) + !$EXP[Exp_Hubs_SlideInfo] + !$EXP[Exp_InfoDialogs] + !$EXP[Hub_Spotlight_Visible_Expression] + Integer.IsEqual(Window.Property(TMDBHelper.WidgetContainer),$PARAM[id]) + !String.IsEmpty(Container($PARAM[id]).ListItem.Plot)</visible>\n            <include>Home_Info_Animation</include>\n            <right>120</right>\n            <width>700</width>\n            <top>179</top>\n            <height>283</height>\n            <!-- ABUKARIM: plot box 4.6.21 (hub info): glass inside the page margin, centred on the info column -->\n            <!-- probes: invisible copies of the plot, one per line count (line = 35 px);\n                 Container(id).NumPages = 1 when the plot fits that height -->\n            <control type="textbox" id="93$PARAM[id]1">\n                <width>700</width>\n                <height>38</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n            </control>\n            <control type="textbox" id="93$PARAM[id]2">\n                <width>700</width>\n                <height>73</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n            </control>\n            <control type="textbox" id="93$PARAM[id]3">\n                <width>700</width>\n                <height>108</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n            </control>\n            <control type="textbox" id="93$PARAM[id]4">\n                <width>700</width>\n                <height>143</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n            </control>\n            <control type="textbox" id="93$PARAM[id]5">\n                <width>700</width>\n                <height>178</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n            </control>\n            <control type="textbox" id="93$PARAM[id]6">\n                <width>700</width>\n                <height>213</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n            </control>\n            <control type="textbox" id="93$PARAM[id]7">\n                <width>700</width>\n                <height>248</height>\n                <font>font_mini_plot</font>\n                <textcolor>00FFFFFF</textcolor>\n                <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n            </control>\n            <!-- the box: the smallest height that holds the plot, centred on the info column -->\n            <control type="group">\n                <visible>!String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(93$PARAM[id]1).NumPages,1)</visible>\n                <top>122</top>\n                <height>38</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="textbox">\n                        <height>38</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>38</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(93$PARAM[id]2).NumPages,1) + !String.IsEqual(Container(93$PARAM[id]1).NumPages,1)</visible>\n                <top>105</top>\n                <height>73</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="textbox">\n                        <height>73</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>73</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(93$PARAM[id]3).NumPages,1) + !String.IsEqual(Container(93$PARAM[id]2).NumPages,1)</visible>\n                <top>87</top>\n                <height>108</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="textbox">\n                        <height>108</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>108</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(93$PARAM[id]4).NumPages,1) + !String.IsEqual(Container(93$PARAM[id]3).NumPages,1)</visible>\n                <top>70</top>\n                <height>143</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="textbox">\n                        <height>143</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>143</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(93$PARAM[id]5).NumPages,1) + !String.IsEqual(Container(93$PARAM[id]4).NumPages,1)</visible>\n                <top>52</top>\n                <height>178</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="textbox">\n                        <height>178</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>178</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(93$PARAM[id]6).NumPages,1) + !String.IsEqual(Container(93$PARAM[id]5).NumPages,1)</visible>\n                <top>35</top>\n                <height>213</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="textbox">\n                        <height>213</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>213</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(93$PARAM[id]7).NumPages,1) + !String.IsEqual(Container(93$PARAM[id]6).NumPages,1)</visible>\n                <top>17</top>\n                <height>248</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="textbox">\n                        <height>248</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>248</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>!String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + !String.IsEqual(Container(93$PARAM[id]7).NumPages,1)</visible>\n                <top>0</top>\n                <height>283</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="textbox">\n                        <height>283</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <autoscroll delay="8000" time="3000" repeat="10000">true</autoscroll>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>283</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <autoscroll delay="8000" time="3000" repeat="10000">true</autoscroll>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(93$PARAM[id]1).NumPages,1)</visible>\n                <top>95</top>\n                <height>92</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="label">\n                        <height>44</height>\n                        <font>font_main_bold</font>\n                        <textcolor>main_fg_100</textcolor>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Season,S,]$INFO[Container($PARAM[id]).ListItem.Episode,E, · ]$INFO[Container($PARAM[id]).ListItem.Title]</label>\n                    </control>\n                    <control type="textbox">\n                        <height>38</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>38</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(93$PARAM[id]2).NumPages,1) + !String.IsEqual(Container(93$PARAM[id]1).NumPages,1)</visible>\n                <top>78</top>\n                <height>127</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="label">\n                        <height>44</height>\n                        <font>font_main_bold</font>\n                        <textcolor>main_fg_100</textcolor>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Season,S,]$INFO[Container($PARAM[id]).ListItem.Episode,E, · ]$INFO[Container($PARAM[id]).ListItem.Title]</label>\n                    </control>\n                    <control type="textbox">\n                        <height>73</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>73</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(93$PARAM[id]3).NumPages,1) + !String.IsEqual(Container(93$PARAM[id]2).NumPages,1)</visible>\n                <top>60</top>\n                <height>162</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="label">\n                        <height>44</height>\n                        <font>font_main_bold</font>\n                        <textcolor>main_fg_100</textcolor>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Season,S,]$INFO[Container($PARAM[id]).ListItem.Episode,E, · ]$INFO[Container($PARAM[id]).ListItem.Title]</label>\n                    </control>\n                    <control type="textbox">\n                        <height>108</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>108</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(93$PARAM[id]4).NumPages,1) + !String.IsEqual(Container(93$PARAM[id]3).NumPages,1)</visible>\n                <top>43</top>\n                <height>197</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="label">\n                        <height>44</height>\n                        <font>font_main_bold</font>\n                        <textcolor>main_fg_100</textcolor>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Season,S,]$INFO[Container($PARAM[id]).ListItem.Episode,E, · ]$INFO[Container($PARAM[id]).ListItem.Title]</label>\n                    </control>\n                    <control type="textbox">\n                        <height>143</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>143</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(93$PARAM[id]5).NumPages,1) + !String.IsEqual(Container(93$PARAM[id]4).NumPages,1)</visible>\n                <top>25</top>\n                <height>232</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="label">\n                        <height>44</height>\n                        <font>font_main_bold</font>\n                        <textcolor>main_fg_100</textcolor>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Season,S,]$INFO[Container($PARAM[id]).ListItem.Episode,E, · ]$INFO[Container($PARAM[id]).ListItem.Title]</label>\n                    </control>\n                    <control type="textbox">\n                        <height>178</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>178</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(93$PARAM[id]6).NumPages,1) + !String.IsEqual(Container(93$PARAM[id]5).NumPages,1)</visible>\n                <top>8</top>\n                <height>267</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="label">\n                        <height>44</height>\n                        <font>font_main_bold</font>\n                        <textcolor>main_fg_100</textcolor>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Season,S,]$INFO[Container($PARAM[id]).ListItem.Episode,E, · ]$INFO[Container($PARAM[id]).ListItem.Title]</label>\n                    </control>\n                    <control type="textbox">\n                        <height>213</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>213</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + String.IsEqual(Container(93$PARAM[id]7).NumPages,1) + !String.IsEqual(Container(93$PARAM[id]6).NumPages,1)</visible>\n                <top>0</top>\n                <height>283</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="label">\n                        <height>44</height>\n                        <font>font_main_bold</font>\n                        <textcolor>main_fg_100</textcolor>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Season,S,]$INFO[Container($PARAM[id]).ListItem.Episode,E, · ]$INFO[Container($PARAM[id]).ListItem.Title]</label>\n                    </control>\n                    <control type="textbox">\n                        <height>229</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <autoscroll delay="8000" time="3000" repeat="10000">true</autoscroll>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>229</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <autoscroll delay="8000" time="3000" repeat="10000">true</autoscroll>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n            <control type="group">\n                <visible>String.IsEqual(Container($PARAM[id]).ListItem.DBType,episode) + !String.IsEqual(Container(93$PARAM[id]7).NumPages,1)</visible>\n                <top>0</top>\n                <height>283</height>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel.png</texture>\n                    <colordiffuse>panel_bg_50</colordiffuse>\n                </control>\n                <control type="image">\n                    <left>-40</left>\n                    <top>-30</top>\n                    <right>-40</right>\n                    <bottom>-30</bottom>\n                    <texture border="48">abk_lucent/panel_edge.png</texture>\n                    <colordiffuse>overlay_soft</colordiffuse>\n                </control>\n                <control type="grouplist">\n                    <orientation>vertical</orientation>\n                    <itemgap>10</itemgap>\n                    <control type="label">\n                        <height>44</height>\n                        <font>font_main_bold</font>\n                        <textcolor>main_fg_100</textcolor>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Season,S,]$INFO[Container($PARAM[id]).ListItem.Episode,E, · ]$INFO[Container($PARAM[id]).ListItem.Title]</label>\n                    </control>\n                    <control type="textbox">\n                        <height>229</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>right</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <autoscroll delay="8000" time="3000" repeat="10000">true</autoscroll>\n                        <visible>String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                    <control type="textbox">\n                        <height>229</height>\n                        <font>font_mini_plot</font>\n                        <textcolor>main_fg_90</textcolor>\n                        <align>left</align>\n                        <label>$INFO[Container($PARAM[id]).ListItem.Plot]</label>\n                        <autoscroll delay="8000" time="3000" repeat="10000">true</autoscroll>\n                        <visible>!String.StartsWith(System.Language,Arabic)</visible>\n                    </control>\n                </control>\n            </control>\n        </control>\n',
        'already_patched_check': '<!-- ABUKARIM: plot box 4.6.21 (hub info): glass inside the page margin, centred on the info column -->',
        'description': 'AF3 Plot on the Right - hub info box margin (upgrade from 4.6.19)',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes_Info.xml'),
        'not_found_ok': True,
        'old': '                <itemgap>0</itemgap>\n\n                <control type="group" description="Avoid grouplist chop with spacer">\n                    <height>20</height>\n                </control>\n',
        'new': '                <itemgap>0</itemgap>\n\n                <control type="group" description="Avoid grouplist chop with spacer">\n                    <height>20</height>\n                </control>\n                <!-- ABUKARIM: plot on the right - the info column moves down to sit above the row title -->\n                <control type="group">\n                    <visible>$PARAM[plotright_genre]</visible>\n                    <height>49</height>\n                </control>\n',
        'already_patched_check': '<!-- ABUKARIM: plot on the right - the info column moves down',
        'description': 'AF3 Plot on the Right - info column moves down',
    },

    # 4.6.21: a running time of 0 (not out yet) showed "0 minutes".
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes_Info.xml'),
        'not_found_ok': True,
        'old': '<param name="visible">!String.IsEmpty($PARAM[container]$PARAM[listitem].Duration) + Integer.IsEqual($PARAM[container]$PARAM[listitem].Duration(h),0) + ',
        'new': '<param name="visible">!String.IsEmpty($PARAM[container]$PARAM[listitem].Duration) + Integer.IsEqual($PARAM[container]$PARAM[listitem].Duration(h),0) + !Integer.IsEqual($PARAM[container]$PARAM[listitem].Duration(m),0) + ',
        'already_patched_check': '<param name="visible">!String.IsEmpty($PARAM[container]$PARAM[listitem].Duration) + Integer.IsEqual($PARAM[container]$PARAM[listitem].Duration(h),0) + !Integer.IsEqual($PARAM[container]$PARAM[listitem].Duration(m),0) + ',
        'description': 'AF3 - info line: no "0 minutes" (one-row)',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes_u3k.xml'),
        'not_found_ok': True,
        'old': '<param name="visible">!String.IsEmpty($PARAM[container]$PARAM[listitem].Duration) + Integer.IsEqual($PARAM[container]$PARAM[listitem].Duration(h),0) + ',
        'new': '<param name="visible">!String.IsEmpty($PARAM[container]$PARAM[listitem].Duration) + Integer.IsEqual($PARAM[container]$PARAM[listitem].Duration(h),0) + !Integer.IsEqual($PARAM[container]$PARAM[listitem].Duration(m),0) + ',
        'already_patched_check': '<param name="visible">!String.IsEmpty($PARAM[container]$PARAM[listitem].Duration) + Integer.IsEqual($PARAM[container]$PARAM[listitem].Duration(h),0) + !Integer.IsEqual($PARAM[container]$PARAM[listitem].Duration(m),0) + ',
        'description': 'AF3 - info line: no "0 minutes" (two-row)',
    },

    # 4.6.23: genre directly under the title (logo), then the info rows; a
    # little more air between the lines on Home while the plot is on the
    # right: the two-line bar's second row 8 px lower (48 px rhythm: badges -
    # date line - ratings), the top spacer 49 px so the column keeps its
    # bottom above the row title. The genre block of 4.6.16 - 4.6.22 (between
    # the info line and the ratings) is taken out.
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes_Info.xml'),
        'not_found_ok': True,
        'old': '                <!-- ABUKARIM: genre line while the plot is on the right (it rides on the plot block otherwise) -->\n                <control type="group">\n                    <visible>$PARAM[plotright_genre] + !String.IsEmpty($PARAM[container]$PARAM[listitem].Genre)</visible>\n                    <height>24</height>\n                    <control type="label">\n                        <left>40</left>\n                        <top>-11</top>\n                        <height>40</height>\n                        <width>$PARAM[plotwidth]</width>\n                        <font>font_main_bold</font>\n                        <textcolor>$PARAM[colordiffuse]_90</textcolor>\n                        <label>$INFO[$PARAM[container]$PARAM[listitem].Genre]</label>\n                    </control>\n                </control>\n\n',
        'new': '',
        # no "done" marker can exist for a removal: the entry just finds
        # nothing to do once the old block is gone (not_found_ok)
        'already_patched_check': '<!-- ABUKARIM: (no marker) -->',
        'fallback_pattern': r'[ \t]*<!-- ABUKARIM: genre line while the plot is on the right[^\n]*-->\n[ \t]*<control type="group">\n(?:(?![ \t]*<!-- ).*\n)*?[ \t]*</control>\n[ \t]*</control>\n\n',
        'fallback_repl': '',
        'description': 'AF3 Plot on the Right - old genre line out (moved under the title)',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes_Info.xml'),
        'not_found_ok': True,
        'old': '                <!-- ABUKARIM: plot on the right - the info column moves down to sit above the row title -->\n                <control type="group">\n                    <visible>$PARAM[plotright_genre]</visible>\n                    <height>64</height>\n                </control>\n',
        'new': '                <!-- ABUKARIM: plot on the right - the info column moves down to sit above the row title -->\n                <control type="group">\n                    <visible>$PARAM[plotright_genre]</visible>\n                    <height>49</height>\n                </control>\n',
        'already_patched_check': '                <!-- ABUKARIM: plot on the right - the info column moves down to sit above the row title -->\n                <control type="group">\n                    <visible>$PARAM[plotright_genre]</visible>\n                    <height>49</height>\n                </control>\n',
        'description': 'AF3 Plot on the Right - info column spacer 49 (upgrade)',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes_u3k.xml'),
        'not_found_ok': True,
        # 4.6.24: exact old = the 4.6.23 line pair (replaced in one go); a stock
        # skin goes through the regex fallback (the centertop 75 line)
        'old': '\t\t\t\t\t<centertop>75</centertop>\n\t\t\t\t\t<animation effect="slide" end="0,8" time="0" condition="Skin.HasSetting(abk.plotright) + Window.IsActive(Home)">Conditional</animation>  <!-- ABUKARIM: plot on the right - airier rows -->\n',
        'new': '\t\t\t\t\t<centertop>75</centertop>\n\t\t\t\t\t<animation effect="slide" end="0,-40" time="0" condition="$PARAM[plotright]">Conditional</animation>  <!-- ABUKARIM: plot on the right - date line first -->\n',
        'already_patched_check': '<!-- ABUKARIM: plot on the right - date line first -->',
        'fallback_pattern': r'(\t*<centertop>75</centertop>\n)',
        'fallback_repl': '\\1' + '\t\t\t\t\t<animation effect="slide" end="0,-40" time="0" condition="$PARAM[plotright]">Conditional</animation>  <!-- ABUKARIM: plot on the right - date line first -->\n',
        'description': 'AF3 Plot on the Right - airier two-line info bar',
    },

    # 4.6.24 (screenshot 2026-10-31 10:10): the quality badges (SD / SDR /
    # AAC / 1.0) move to the bottom of the info column: title, genre, date
    # line, ratings, badges - 48 px apart. Done with conditional slides that
    # only run for the Info_Panel of a hub with the plot on the right: the
    # panel passes its plotright_genre condition down as a "plotright" param
    # (Info_Line -> Info_Line_TwoRow_U3k, Info_Meta; default false, so every
    # other use of those includes is untouched). Date line up 40, ratings
    # (Info_Meta) up 52, badges row down 96.
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes_Info.xml'),
        'not_found_ok': True,
        'old': '<param name="visible">$PARAM[visible_line]</param>\n                </include>',
        'new': '<param name="visible">$PARAM[visible_line]</param>\n                    <param name="plotright">$PARAM[plotright_genre]</param>  <!-- ABUKARIM: plot right order -->\n                </include>',
        'already_patched_check': '<param name="visible">$PARAM[visible_line]</param>\n                    <param name="plotright">$PARAM[plotright_genre]</param>  <!-- ABUKARIM: plot right order -->\n                </include>',
        'description': 'AF3 Plot on the Right - Info_Panel -> Info_Line param',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes_Info.xml'),
        'not_found_ok': True,
        'old': '<param name="visible">$PARAM[visible_meta]</param>\n                </include>',
        'new': '<param name="visible">$PARAM[visible_meta]</param>\n                    <param name="plotright">$PARAM[plotright_genre]</param>  <!-- ABUKARIM: plot right order -->\n                </include>',
        'already_patched_check': '<param name="visible">$PARAM[visible_meta]</param>\n                    <param name="plotright">$PARAM[plotright_genre]</param>  <!-- ABUKARIM: plot right order -->\n                </include>',
        'description': 'AF3 Plot on the Right - Info_Panel -> Info_Meta param',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes_Info.xml'),
        'not_found_ok': True,
        'old': '<param name="override">false</param>\n        <definition>\n            <control type="group">\n                <visible>$PARAM[visible] + !Skin.HasSetting(InfoBar.TwoRow)</visible>',
        'new': '<param name="override">false</param>\n        <param name="plotright">false</param>  <!-- ABUKARIM: plot right order -->\n        <definition>\n            <control type="group">\n                <visible>$PARAM[visible] + !Skin.HasSetting(InfoBar.TwoRow)</visible>',
        'already_patched_check': '<param name="override">false</param>\n        <param name="plotright">false</param>  <!-- ABUKARIM: plot right order -->\n        <definition>\n            <control type="group">\n                <visible>$PARAM[visible] + !Skin.HasSetting(InfoBar.TwoRow)</visible>',
        'description': 'AF3 Plot on the Right - Info_Line default param',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes_Info.xml'),
        'not_found_ok': True,
        'old': '                <param name="override">$PARAM[override]</param>\n                <param name="colordiffuse">$PARAM[colordiffuse]</param>\n            </include>\n        </definition>',
        'new': '                <param name="override">$PARAM[override]</param>\n                <param name="colordiffuse">$PARAM[colordiffuse]</param>\n                <param name="plotright">$PARAM[plotright]</param>  <!-- ABUKARIM: plot right order -->\n            </include>\n        </definition>',
        'already_patched_check': '                <param name="override">$PARAM[override]</param>\n                <param name="colordiffuse">$PARAM[colordiffuse]</param>\n                <param name="plotright">$PARAM[plotright]</param>  <!-- ABUKARIM: plot right order -->\n            </include>\n        </definition>',
        'description': 'AF3 Plot on the Right - Info_Line -> two-line bar param',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes_u3k.xml'),
        'not_found_ok': True,
        'old': '<param name="override">false</param>\n        <definition>\n            <control type="group">\n                <visible>$PARAM[visible] + Skin.HasSetting(InfoBar.TwoRow)</visible>',
        'new': '<param name="override">false</param>\n        <param name="plotright">false</param>  <!-- ABUKARIM: plot right order -->\n        <definition>\n            <control type="group">\n                <visible>$PARAM[visible] + Skin.HasSetting(InfoBar.TwoRow)</visible>',
        'already_patched_check': '<param name="override">false</param>\n        <param name="plotright">false</param>  <!-- ABUKARIM: plot right order -->\n        <definition>\n            <control type="group">\n                <visible>$PARAM[visible] + Skin.HasSetting(InfoBar.TwoRow)</visible>',
        'description': 'AF3 Plot on the Right - two-line bar default param',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes_u3k.xml'),
        'not_found_ok': True,
        'old': '                    <centertop>35</centertop>\n',
        'new': '                    <centertop>35</centertop>\n                    <animation effect="slide" end="0,96" time="0" condition="$PARAM[plotright]">Conditional</animation>  <!-- ABUKARIM: plot on the right - badges last -->\n',
        'already_patched_check': '<!-- ABUKARIM: plot on the right - badges last -->',
        'description': 'AF3 Plot on the Right - badges row to the bottom',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes_Info.xml'),
        'not_found_ok': True,
        'old': '<param name="ratings_visible">true</param>\n        <definition>',
        'new': '<param name="ratings_visible">true</param>\n        <param name="plotright">false</param>  <!-- ABUKARIM: plot right order -->\n        <definition>',
        'already_patched_check': '<param name="ratings_visible">true</param>\n        <param name="plotright">false</param>  <!-- ABUKARIM: plot right order -->\n        <definition>',
        'description': 'AF3 Plot on the Right - Info_Meta default param',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes_Info.xml'),
        'not_found_ok': True,
        'old': '                <left>40</left>\n                <include>Info_Line_Height_U3k</include>\n                <visible>$PARAM[visible]</visible>\n',
        'new': '                <left>40</left>\n                <include>Info_Line_Height_U3k</include>\n                <visible>$PARAM[visible]</visible>\n                <animation effect="slide" end="0,-52" time="0" condition="$PARAM[plotright]">Conditional</animation>  <!-- ABUKARIM: plot on the right - ratings up -->\n',
        'already_patched_check': '<!-- ABUKARIM: plot on the right - ratings up -->',
        'description': 'AF3 Plot on the Right - ratings row up',
    },

    # ── AF3 auto-trailers, ARTWORK mode (3.2.48) - Dex Hub's way ──
    # The trailer plays inside the skin's own artwork frame (its 'FlixArt'
    # video frame), not behind the whole page and not full screen. The
    # engine sets Window(Home).Property(abk.trailer.art) for such a trailer
    # and abk.trailer.visible only once its frames are rolling; the frame then
    # fades in over 600 ms, so the artwork never gives way to a black frame.
    # Any other video (and a trailer in the other two modes) uses the skin's
    # background video exactly as before: with no trailer the properties are
    # empty and AF3 behaves as unpatched. The anchor is the same AF3 text Dex
    # Hub's own trailer patch (af3patch.py) edits; a skin Dex Hub already
    # patched is handled by the regex fallback.
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes_Background.xml'),
        'toggle': 'af3_trailers',
        'feature': 'af3_trailers',
        'not_found_ok': True,
        'old': ('            <include condition="![$PARAM[video_background]]">Background_Video_Offscreen</include>\n'
                '            <include condition="$PARAM[video_background]">Background_Video</include>\n'),
        'new': ('            <!-- ABUKARIM: trailer in the artwork -->\n'
                '            <control type="group">\n'
                '                <visible>String.IsEmpty(Window(Home).Property(abk.trailer.art))</visible>\n'
                '                <include condition="![$PARAM[video_background]]">Background_Video_Offscreen</include>\n'
                '                <include condition="$PARAM[video_background]">Background_Video</include>\n'
                '            </control>\n'
                '            <control type="group">\n'
                '                <visible>!String.IsEmpty(Window(Home).Property(abk.trailer.art)) + '
                '!String.IsEmpty(Window(Home).Property(abk.trailer.visible)) + Player.HasVideo</visible>\n'
                '                <animation effect="fade" start="0" end="100" time="600" tween="sine" easing="out">Visible</animation>\n'
                '                <include>Background_Video_FlixArt</include>\n'
                '            </control>\n'),
        'already_patched_check': '<!-- ABUKARIM: trailer in the artwork -->',
        # Dex Hub's trailer patch is in: its two groups learn ours too
        'fallback_pattern': (r'<visible>!\$EXP\[DexHub_Trailer\]</visible>(\s*'
                             r'<include condition="!\[\$PARAM\[video_background\]\]">Background_Video_Offscreen</include>'
                             r'\s*<include condition="\$PARAM\[video_background\]">Background_Video</include>'
                             r'\s*</control>\s*<control type="group">\s*)'
                             r'<visible>\$EXP\[DexHub_Trailer\]</visible>'),
        'fallback_repl': ('<visible>!$EXP[DexHub_Trailer] + String.IsEmpty(Window(Home).Property(abk.trailer.art))</visible>'
                          '<!-- ABUKARIM: trailer in the artwork -->\\1'
                          '<visible>$EXP[DexHub_Trailer] | [!String.IsEmpty(Window(Home).Property(abk.trailer.art)) + '
                          '!String.IsEmpty(Window(Home).Property(abk.trailer.visible)) + Player.HasVideo]</visible>'),
        'description': 'AF3 Includes_Background.xml - auto-trailer fades in inside the artwork frame',
    },
    {   # 3.2.48: while an artwork trailer opens, AF3's busy loader (waves)
        # stays hidden - the engine closes Kodi's spinner at once, the
        # loader behind it would still flash over the artwork. Builds on the
        # busy-waves entry just above (its text is the anchor).
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes_Background.xml'),
        'toggle': 'af3_trailers',
        'feature': 'af3_trailers',
        'not_found_ok': True,
        'old': '!Skin.HasSetting(abk.nobusywaves)</visible>',
        'new': ('!Skin.HasSetting(abk.nobusywaves) + '
                'String.IsEmpty(Window(Home).Property(abk.trailer.opening))</visible>'),
        'already_patched_check': 'Window(Home).Property(abk.trailer.opening)',
        'description': 'AF3 busy loader - hidden while an auto-trailer opens',
    },
    # ── TMDbHelper: dead-player guard (by ABUKARIM TOOLS) ──
    # onAVChange / onAVStarted call get_playingitem() while the player is
    # tearing down; getPlayingFile() then raises RuntimeError ("Kodi is not
    # playing any file"), the callback thread dies and Kodi warns about memory
    # leaks (seen every teardown as player.py:414). Guard with isPlaying() +
    # try/except RuntimeError and collapse the doubled getPlayingFile() call.
    {
        'addon_id': 'plugin.video.themoviedb.helper',
        'rel_path': os.path.join('resources', 'tmdbhelper', 'lib', 'monitor', 'player.py'),
        'old': (
            "    def get_playingitem(self):\n"
            "        # Check that video other than dummy splash video is playing\n"
            "        if self.getPlayingFile() and self.getPlayingFile().endswith('dummy.mp4'):\n"
            "            self.reset_properties()\n"
            "            return\n"
        ),
        'new': (
            "    def get_playingitem(self):\n"
            "        # Check that video other than dummy splash video is playing\n"
            "        # -- TMDbHelper dead-player guard (by ABUKARIM TOOLS) --\n"
            "        try:\n"
            "            if not self.isPlaying():\n"
            "                self.reset_properties()\n"
            "                return\n"
            "            _abk_playing_file = self.getPlayingFile()\n"
            "        except RuntimeError:\n"
            "            self.reset_properties()\n"
            "            return\n"
            "        if _abk_playing_file and _abk_playing_file.endswith('dummy.mp4'):\n"
            "            self.reset_properties()\n"
            "            return\n"
        ),
        'already_patched_check': '# -- TMDbHelper dead-player guard (by ABUKARIM TOOLS) --',
        'fallback_pattern': r"        if self\.getPlayingFile\(\) and self\.getPlayingFile\(\)\.endswith\('dummy\.mp4'\):\n            self\.reset_properties\(\)\n            return\n",
        'fallback_repl': (
            "        # -- TMDbHelper dead-player guard (by ABUKARIM TOOLS) --\n"
            "        try:\n"
            "            if not self.isPlaying():\n"
            "                self.reset_properties()\n"
            "                return\n"
            "            _abk_playing_file = self.getPlayingFile()\n"
            "        except RuntimeError:\n"
            "            self.reset_properties()\n"
            "            return\n"
            "        if _abk_playing_file and _abk_playing_file.endswith('dummy.mp4'):\n"
            "            self.reset_properties()\n"
            "            return\n"
        ),
        'toggle': 'tmdbh_stability',
        'description': 'TMDbHelper player.py \u2013 dead-player guard (getPlayingFile RuntimeError)',
    },
    # ── TMDbHelper: genres follow the language setting (3.4.4) ──
    # Genre names sit in ItemDetails.db with NO iso_language column (unlike
    # title/plot in the translation table), and later writes only fill NULLs
    # (ON CONFLICT ... ifnull), so an item first cached in English keeps English
    # genres forever after switching TMDbHelper to ar-SA. This stamps the
    # language inside ItemDetails.db; on the first DB init of a Kodi session
    # where it differs (or no stamp yet) it clears the genre rows and expires
    # their items, so TMDbHelper refetches them in the current language.
    # Runs inside TMDbHelper's own init (no file deletion, no race with Kodi).
    {
        'addon_id': 'plugin.video.themoviedb.helper',
        'rel_path': os.path.join('resources', 'tmdbhelper', 'lib', 'items', 'database', 'database.py'),
        'toggle': 'tmdbh_genre_lang',
        # 'old' = a v1-patched file (upgraded in place); a stock file goes
        # through the regex below instead.
        'old': "    cache_filename = 'ItemDetails.db'\n" + _TMDBH_GENRE_LANG_BLOCK_V1,
        'new': "    cache_filename = 'ItemDetails.db'\n" + _TMDBH_GENRE_LANG_BLOCK,
        'already_patched_check': '# -- TMDbHelper genre language refresh v2 (by ABUKARIM TOOLS) --',
        'fallback_pattern': r"    cache_filename = [\"']ItemDetails\.db[\"'][ \t]*\r?\n(?!\r?\n    # -- TMDbHelper genre language refresh)",
        'fallback_repl': r'\g<0>' + _TMDBH_GENRE_LANG_BLOCK,
        'description': 'TMDbHelper database.py – refresh cached genres when the language changes',
        'max_version': '6.99.99',          # 7.x: see the v7 entry below
    },
    {
        'addon_id': 'plugin.video.themoviedb.helper',
        'rel_path': os.path.join('resources', 'tmdbhelper', 'lib', 'query', 'database', 'database.py'),
        'toggle': 'tmdbh_genre_lang',
        'old': "    cache_filename = 'ItemQueries.db'\n",
        'new': "    cache_filename = 'ItemQueries.db'\n" + _TMDBH_GENRE_LIST_LANG_BLOCK,
        'already_patched_check': '# -- TMDbHelper genre list language refresh (by ABUKARIM TOOLS) --',
        'fallback_pattern': r"    cache_filename = [\"']ItemQueries\.db[\"'][ \t]*\r?\n",
        'fallback_repl': r'\g<0>' + _TMDBH_GENRE_LIST_LANG_BLOCK,
        'description': 'TMDbHelper query database.py \u2013 refresh the global genre list when the language changes',
        'max_version': '6.99.99',          # 7.x: see the v7 entry below
    },
    {
        'addon_id': 'plugin.video.themoviedb.helper',
        'rel_path': os.path.join('resources', 'tmdbhelper', 'lib', 'items', 'database', 'database.py'),
        'toggle': 'tmdbh_genre_lang',
        'min_version': '7.0.0',
        'old': _TMDBH7_GENRE_ANCHOR,
        'new': _TMDBH7_GENRE_ANCHOR + _TMDBH7_GENRE_BLOCK,
        'already_patched_check': '# -- TMDbHelper genre language refresh v7 (by ABUKARIM TOOLS) --',
        'description': 'TMDbHelper 7 database.py - refresh cached genres when the language changes',
    },
    # ── TMDbHelper: thread cap (3.3.3); invoker reuse removed (3.4.14) ──
    # 2026-10-13 OOM kill on the AM9 (4 GB, no swap): kodi.bin reached 2.08 GB
    # anon-rss opening AF3's Korean hub after TraktHubs added 7 widgets. Stock
    # max_threads default is 0 = UNLIMITED in jurialmunkey.ParallelThread, so
    # every widget spawns one thread per item. The thread cap (tmdbh_stability)
    # stays. 3.4.14: the "Keep Python Warm" toggle (tmdbh_invoker,
    # reuselanguageinvoker=true, 3.3.3-3.4.13) is REMOVED - 2026-10-19 AM9
    # crashlog: SIGSEGV in libpython while a reused TMDbHelper interpreter
    # was being torn down as three new ones started. This always-on entry
    # puts TMDbHelper's stock 'false' back on boxes the toggle had changed
    # (a no-op on stock files). Kodi reads addon.xml at start-up, so it takes
    # effect after the next Kodi restart.
    {
        'addon_id': 'plugin.video.themoviedb.helper',
        'rel_path': 'addon.xml',
        'old': '<reuselanguageinvoker>true</reuselanguageinvoker>',
        'new': '<reuselanguageinvoker>false</reuselanguageinvoker>',
        'already_patched_check': '<reuselanguageinvoker>false</reuselanguageinvoker>',
        'fallback_pattern': r'<reuselanguageinvoker>\s*true\s*</reuselanguageinvoker>',
        'fallback_repl': '<reuselanguageinvoker>false</reuselanguageinvoker>',
        'not_found_ok': True,
        'description': 'TMDbHelper addon.xml – restore stock reuselanguageinvoker=false (Keep Python Warm removed)',
    },
    {
        'addon_id': 'plugin.video.themoviedb.helper',
        'rel_path': os.path.join('resources', 'settings.xml'),
        'toggle': 'tmdbh_stability',
        'old': '',
        'new': '',
        'already_patched_check': '<!-- ABK max_threads=3 -->',
        'fallback_pattern': (r'(<setting id="max_threads"[^>]*>'
                             r'(?:(?!</setting>)[\s\S])*?<default>)\s*\d+\s*(</default>)'),
        'fallback_repl': r'<!-- ABK max_threads=3 -->\g<1>3\g<2>',
        'not_found_ok': True,
        'description': 'TMDbHelper settings.xml – max_threads default 3 (was 0 = unlimited)',
    },
    {   # A value saved in userdata beats the default: force it to 3 too.
        # default="true" rows follow the new default, but rewriting them is harmless.
        'addon_id': 'plugin.video.themoviedb.helper',
        'base': 'addon_data',
        'rel_path': 'settings.xml',
        'toggle': 'tmdbh_stability',
        'old': '',
        'new': '',
        'already_patched_check': '<setting id="max_threads">3</setting>',
        # 3.3.4: only an unlimited (0) / empty / self-closing value is
        # rewritten - a number the user picked is kept (3.3.3 matched \d*).
        'fallback_pattern': r'<setting id="max_threads"(?: default="true")?\s*>\s*0?\s*</setting>|<setting id="max_threads"(?: default="true")?\s*/>',
        'fallback_repl': '<setting id="max_threads">3</setting>',
        'not_found_ok': True,
        'description': 'TMDbHelper userdata settings.xml – max_threads=3',
    },
    # ── Last Played: capture engine for TMDbHelper / Fen Light playback (3.2.11) ──
    # Stock 6.4.0 never recorded TMDbHelper -> player add-on playback on Kodi 21/22:
    # the dummy.mp4 splash fired the stop callback with empty data, the real stream
    # was read in onPlayBackStarted before its info settled and anything not typed
    # movie/episode was dropped ("videos" is off by default); the saved link was the
    # debrid URL, dead the next day. Whole service file is replaced (same JSON
    # format, so the stock addon.py lists it unchanged); the service is restarted
    # after a write so it takes effect without rebooting Kodi.
    # ── a4kSubtitles: quiet mode (3.2.11) ──
    # The build ships OpenSubtitles / SubDL / SubSource enabled without accounts,
    # so every search popped "requires authentication" / "requires API Key"
    # notifications (plus "IMDB ID is not provided" for plugin items). Those nags
    # now go to the log only; real messages still show. logger.debug() also
    # stops writing player_props / "no subtitles found for ..." at INFO level
    # unless Kodi's debug logging is on.
    {
        'addon_id': 'service.subtitles.a4ksubtitles',
        'rel_path': os.path.join('a4kSubtitles', 'lib', 'kodi.py'),
        'old': '',
        'new': '',
        'already_patched_check': '# -- a4kSubtitles quiet nags (by ABUKARIM TOOLS) --',
        'fallback_pattern': r'(def notification\(text, time=3000\):[^\n]*\n)',
        'fallback_repl': (
            r'\1'
            "    # -- a4kSubtitles quiet nags (by ABUKARIM TOOLS) --\n"
            "    _abk_t = str(text).lower()\n"
            "    if any(_k in _abk_t for _k in ('requires authentication', 'requires api key',\n"
            "                                   'authentication failed', 'imdb id is not provided',\n"
            "                                   'no downloads left', 'manual search is not supported')):\n"
            "        xbmc.log('a4kSubtitles (silenced): %s' % text, xbmc.LOGINFO)\n"
            "        return\n"
        ),
        'not_found_ok': True,
        'toggle': 'a4ksubs_quiet',
        'description': 'a4kSubtitles kodi.py - silence missing-account / API-key notifications',
    },
    {
        'addon_id': 'service.subtitles.a4ksubtitles',
        'rel_path': os.path.join('a4kSubtitles', 'lib', 'logger.py'),
        'old': 'def debug(message):\n    __log(message, notice_type)\n',
        'new': ('def debug(message):\n'
                '    # -- a4kSubtitles quiet debug (by ABUKARIM TOOLS) --\n'
                '    if not __get_debug_logenabled():\n'
                '        return\n'
                '    __log(message, notice_type)\n'),
        'already_patched_check': '# -- a4kSubtitles quiet debug (by ABUKARIM TOOLS) --',
        'not_found_ok': True,
        'toggle': 'a4ksubs_quiet',
        'description': 'a4kSubtitles logger.py - debug chatter only when Kodi debug logging is on',
    },
    # ── AF3: Subtitle Buttons (3.3.2, toggle 'af3_subtools') ──
    # Two OSD buttons right after the Subtitles button (6007) in the AF3 player
    # bar: DexSubtitles AutoSync (dexsync.png) and Subtitle Cycler
    # (subcycler.png). Icons are shipped into extras/icons; the DexSubtitles
    # launcher is shipped INTO service.subtitles.dexworld so it runs with that
    # add-on's context and its own autosync.py. The cycler button runs
    # script.subtitle.cycler, or - when it is missing/disabled - RunPlugin
    # mode=subtitle_cycler, which installs it from repository.taiseer first
    # (subtitle_tools.py). All not_found_ok: a missing skin/add-on is a skip.
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('extras', 'icons', 'dexsync.png'),
        'toggle': 'af3_subtools',
        'inject_file': True,
        'binary': True,
        'replace': True,
        'not_found_ok': True,
        'inject_source': os.path.join('resources', 'af3_subtools', 'dexsync.png'),
        'description': 'AF3 Subtitle Buttons - DexSubtitles icon',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('extras', 'icons', 'subcycler.png'),
        'toggle': 'af3_subtools',
        'inject_file': True,
        'binary': True,
        'replace': True,
        'not_found_ok': True,
        'inject_source': os.path.join('resources', 'af3_subtools', 'subcycler.png'),
        'description': 'AF3 Subtitle Buttons - Subtitle Cycler icon',
    },
    {
        'addon_id': 'service.subtitles.dexworld',
        'rel_path': 'abk_osd_sync.py',
        'toggle': 'af3_subtools',
        'inject_file': True,
        'binary': True,
        'replace': True,
        'not_found_ok': True,
        'inject_source': os.path.join('resources', 'af3_subtools', 'abk_osd_sync.py'),
        'description': 'AF3 Subtitle Buttons - DexSubtitles OSD AutoSync launcher',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'VideoOSD.xml'),
        'toggle': 'af3_subtools',
        'not_found_ok': True,
        'old': _AF3_SUBTOOLS_ANCHOR,
        'new': _AF3_SUBTOOLS_ANCHOR + _AF3_SUBTOOLS_XML,
        'already_patched_check': '<!-- ABUKARIM: AF3 subtitle buttons -->',
        'fallback_pattern': r'(<param name="groupid">6107</param>[\s\S]*?</include>)',
        'fallback_repl': r'\1' + _AF3_SUBTOOLS_XML,   # XML has no backslashes
        'description': 'AF3 Subtitle Buttons - OSD buttons after Subtitles',
    },    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes_OSD.xml'),
        'toggle': 'af3_subtools',
        'not_found_ok': True,
        'old': _AF3_SUBTOOLS_POPUP_ANCHOR,
        'new': _AF3_SUBTOOLS_POPUP_XML + _AF3_SUBTOOLS_POPUP_ANCHOR,
        'already_patched_check': '<!-- ABUKARIM: AF3 subtitle buttons (popup slots) -->',
        'fallback_pattern': r'([ \t]*<include content="OSD_CustomDialog_FakeButton" condition="!\[\$PARAM\[button_8\]\]">)',
        'fallback_repl': _AF3_SUBTOOLS_POPUP_XML.replace('\\', '\\\\') + r'\1',
        'description': 'AF3 Subtitle Buttons - matching slots in OSD popups (no duplicate icons)',
    },
    # ── AF3: Subtitle Look button (4.6.2, toggle 'af3_substyle') ──
    # Icon into extras/icons, the button before Video settings in VideoOSD,
    # and a matching popup slot. revert_when_off takes both XML parts out
    # again when the switch is turned off.
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('extras', 'icons', 'substyle.png'),
        'toggle': 'af3_substyle',
        'inject_file': True,
        'binary': True,
        'replace': True,
        'not_found_ok': True,
        'inject_source': os.path.join('resources', 'af3_substyle', 'substyle.png'),
        'description': 'AF3 Subtitle Look - OSD icon',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'VideoOSD.xml'),
        'toggle': 'af3_substyle',
        'not_found_ok': True,
        'old': _AF3_SUBSTYLE_ANCHOR,
        'new': _AF3_SUBSTYLE_XML + _AF3_SUBSTYLE_ANCHOR,
        'already_patched_check': '<!-- ABUKARIM: AF3 subtitle look button -->',
        'revert_when_off': (_AF3_SUBSTYLE_XML + _AF3_SUBSTYLE_ANCHOR, _AF3_SUBSTYLE_ANCHOR),
        'description': 'AF3 Subtitle Look - OSD button (height, size, font)',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes_OSD.xml'),
        'toggle': 'af3_substyle',
        'not_found_ok': True,
        'old': _AF3_SUBTOOLS_POPUP_ANCHOR,
        'new': _AF3_SUBSTYLE_POPUP_XML + _AF3_SUBTOOLS_POPUP_ANCHOR,
        'already_patched_check': '<!-- ABUKARIM: AF3 subtitle look button (popup slot) -->',
        'revert_when_off': (_AF3_SUBSTYLE_POPUP_XML + _AF3_SUBTOOLS_POPUP_ANCHOR, _AF3_SUBTOOLS_POPUP_ANCHOR),
        'description': 'AF3 Subtitle Look - matching slot in OSD popups',
    },
    # ── Lucent theme for Fen Light, Red Light, POV & Umbrella ──
    # 3.4.39: a Toggles-menu feature with one switch per add-on (lucent_toggle.py),
    # gated by 'feature': 'lucent_<profile>' - no longer in the Apply Patches list.
    # Source results + scraping/resolving windows restyled after the Lucent theme
    # for Seren (djdirty60/Seren-Thema). One entry per add-on; lucent_sources.py
    # copies the helper/textures/XMLs, adds fenced hooks, and backs up the stock
    # XMLs so switching the toggle off restores them (see _revert_disabled).
    {'addon_id': 'plugin.video.fenlight', 'lucent': 'fenlight', 'feature': 'lucent_fenlight', 'not_found_ok': True,
     'rel_path': os.path.join('resources', 'skins', 'Default', '1080i', 'sources_results.xml'),
     'old': '', 'new': '', 'description': 'Fen Light - Glass theme source windows'},
    {'addon_id': 'plugin.video.redlight', 'lucent': 'redlight', 'feature': 'lucent_redlight', 'not_found_ok': True,
     'rel_path': os.path.join('resources', 'skins', 'Default', '1080i', 'sources_playback.xml'),
     'old': '', 'new': '', 'description': 'Red Light - Glass theme source windows'},
    {'addon_id': 'plugin.video.pov', 'lucent': 'pov', 'feature': 'lucent_pov', 'not_found_ok': True,
     'rel_path': os.path.join('resources', 'skins', 'Default', '1080i', 'sources_results.xml'),
     'old': '', 'new': '', 'description': 'POV - Glass theme source windows'},
    {'addon_id': 'plugin.video.umbrella', 'lucent': 'umbrella', 'feature': 'lucent_umbrella', 'not_found_ok': True,
     'rel_path': os.path.join('resources', 'skins', 'Default', '1080i', 'source_results.xml'),
     'old': '', 'new': '', 'description': 'Umbrella - Glass theme source windows'},
    # ── POV: metadata memory cache compares a text expiry with a number (4.5.2) ──
    # A movie's meta read back from metacache.db keeps its "expires" column as
    # text, is put in the memory cache (window property) that way, and the next
    # lookup of that title in the session raises TypeError "'<' not supported
    # between instances of 'str' and 'int'" in get_memory_cache - POV then
    # cannot open sources for it (CoreELEC report, kodi.log 2026-10-29).
    {'addon_id': 'plugin.video.pov', 'not_found_ok': True,
     'rel_path': os.path.join('resources', 'lib', 'caches', 'meta_cache.py'),
     'old': "\t\texpiry, meta = self.jsloads(cache_data)\n\t\tif expiry < current_time: return None\n",
     'new': "\t\texpiry, meta = self.jsloads(cache_data)\n\t\ttry:\n\t\t\tif int(expiry) < current_time: return None\n\t\texcept (TypeError, ValueError): return None  # ABK: text expiry from metacache.db\n",
     'already_patched_check': '# ABK: text expiry from metacache.db',
     'description': 'POV meta_cache.py - text expiry in the memory cache no longer breaks source search'},
    # 4.5.4: the real cause - a metacache.db made by an older POV has its
    # columns in another order (... meta, expires instead of ... expires, meta).
    # POV inserts by position, so meta lands in "expires" and the timestamp in
    # "meta"; reading back gives a number as meta ("argument of type 'int' is
    # not a container or iterable" in get_title) or text as expiry. Insert by
    # column name, and treat a row that is not a meta dict as a cache miss so
    # POV fetches it again and the row is rewritten correctly.
    {'addon_id': 'plugin.video.pov', 'not_found_ok': True,
     'rel_path': os.path.join('resources', 'lib', 'caches', 'meta_cache.py'),
     'old': "SET_MOVIE_SHOW = 'INSERT OR REPLACE INTO metadata VALUES (?, ?, ?, ?, ?, ?)'\nSET_SEASON = 'INSERT INTO season_metadata VALUES (?, ?, ?)'\nSET_FUNCTION = 'INSERT INTO function_cache VALUES (?, ?, ?)'\n",
     'new': "SET_MOVIE_SHOW = 'INSERT OR REPLACE INTO metadata (db_type, tmdb_id, imdb_id, tvdb_id, expires, meta) VALUES (?, ?, ?, ?, ?, ?)'  # ABK: by column name\nSET_SEASON = 'INSERT OR REPLACE INTO season_metadata (tmdb_id, expires, meta) VALUES (?, ?, ?)'\nSET_FUNCTION = 'INSERT INTO function_cache (string_id, expires, data) VALUES (?, ?, ?)'\n",
     'already_patched_check': '# ABK: by column name',
     'description': 'POV meta_cache.py - write by column name (metacache.db from an older POV has another column order)'},
    {'addon_id': 'plugin.video.pov', 'not_found_ok': True,
     'rel_path': os.path.join('resources', 'lib', 'caches', 'meta_cache.py'),
     'old': "\t\tif not data: return None\n\t\tmeta, expiry = self.jsloads(data[0]), data[1]\n",
     'new': "\t\tif not data: return None\n\t\ttry: meta, expiry = self.jsloads(data[0]), int(data[1])\n\t\texcept (TypeError, ValueError): return None  # ABK: row written in the wrong columns\n\t\tif not isinstance(meta, (dict, list)): return None\n",
     'already_patched_check': '# ABK: row written in the wrong columns',
     'description': 'POV meta_cache.py - a row written in the wrong columns is a cache miss, not a crash'},
    {'addon_id': 'plugin.video.pov', 'not_found_ok': True,
     'rel_path': os.path.join('resources', 'lib', 'caches', 'meta_cache.py'),
     'old': "\t\tif not cache_data: return None\n\t\treturn self.jsloads(cache_data[0])\n",
     'new': "\t\tif not cache_data: return None\n\t\ttry: int(cache_data[1])\n\t\texcept (TypeError, ValueError): return None  # ABK: function row in the wrong columns\n\t\treturn self.jsloads(cache_data[0])\n",
     'already_patched_check': '# ABK: function row in the wrong columns',
     'description': 'POV meta_cache.py - function cache row written in the wrong columns is a miss'},
    # ── Search All (3.4.48): Toggles > Glass Theme > "Search All add-ons" ──
    # Red Light gets Fen Light's device-select modes back (Fen Light has them);
    # TMDbHelper gets the "AB Search All" player that opens resources/lib/ab_search.py.
    {'addon_id': 'plugin.video.redlight', 'lucent': 'redlight_search', 'feature': 'ab_search', 'not_found_ok': True,
     'rel_path': os.path.join('resources', 'lib', 'modules', 'router.py'),
     'old': '', 'new': '', 'description': 'Red Light - Search All bridge (app_list_sources / app_play_source)'},
    {'addon_id': 'plugin.video.pov', 'lucent': 'pov_search', 'feature': 'ab_search', 'not_found_ok': True,
     'rel_path': os.path.join('resources', 'lib', 'modules', 'entry.py'),
     'old': '', 'new': '', 'description': 'POV - Search All bridge (app_list_sources / app_play_source)'},
    {'addon_id': 'plugin.video.umbrella', 'lucent': 'umbrella_search', 'feature': 'ab_search', 'not_found_ok': True,
     'rel_path': os.path.join('resources', 'lib', 'modules', 'router.py'),
     'old': '', 'new': '', 'description': 'Umbrella - Search All bridge (app_list_sources / app_play_source)'},
    {'addon_id': 'plugin.video.themoviedb.helper', 'base': 'addon_data', 'feature': 'ab_search', 'not_found_ok': True,
     'rel_path': AB_SEARCH_PLAYER, 'inject_file': True, 'old': '', 'new': '',
     'inject_content': _AB_SEARCH_PLAYER_JSON,
     'description': 'TMDbHelper players/abukarim.search_all.json - AB Search All (every add-on in one list)'},
]


# ── script.skinvariables: broken Arabic strings.po (3.3.6) ──
# kodi.log 2026-10-14 05:44:18: 13 x "POParser: missing msgstr line in entry"
# while loading resource.language.ar_sa. script.skinvariables 2.2.8 (taiseer999
# .github.io repo/zips) has the Arabic text on a SECOND msgid line instead of msgstr, so
# Kodi drops those entries and shows English. Each entry rewrites one string
# as a proper msgstr in Modern Standard Arabic (the old text also had English
# "to" / "as" and typos). Always-on bug fix (no toggle); idempotent through
# the msgstr sentinel; skips cleanly once upstream ships a fixed file.
# ── Arctic Fuse 3 on LibreELEC: LibreELEC start-up logo (3.4.2) ──
# User request 2026-10-14: on LibreELEC replace the AF3 start-up logo
# (Includes_Objects.xml Object_StartUp_Logo: CE.png + 'CoreELEC "NG"') with
# extras/icons/libreelec.png + "LibreELEC" at double size, which needs a
# font_logo_xlarge in Includes_Font.xml. Targeted edits, NOT the whole files:
# the supplied Includes_Font.xml / Includes_Objects.xml predate AF3 5.17.0 and
# would delete font_infotag_bold, font_title_info and Object_Statistics_Panel.
# 'os': 'libreelec' = only on LibreELEC (/etc/os-release ID), see _os_id().
# 3.4.19: also matches a logo block an earlier ABK platform patch wrote (its
# "<!-- ABK ... logo -->" marker), so a box that changes platform - CoreELEC 21
# NG upgraded to 22 NO, say - gets the new logo instead of keeping the old one.
_AF3_LOGO_RE = (r'<include name="Object_StartUp_Logo">\s*(?:<!-- ABK [^>]*? logo -->\s*)?'
                r'<control type="grouplist">.*?</control>\s*</control>')
_AF3_LE_LOGO = (
    '<include name="Object_StartUp_Logo">\n'
    '        <!-- ABK LibreELEC logo -->\n'
    '        <control type="grouplist">\n'
    '            <height>260</height>\n'
    '            <centertop>265</centertop>\n'
    '            <orientation>vertical</orientation>\n'
    '            <align>center</align>\n'
    '            <control type="image">\n'
    '                <width>192</width>\n'
    '                <height>192</height>\n'
    '                <centerleft>50%</centerleft>\n'
    '                <aspectratio>keep</aspectratio>\n'
    '                <texture>special://skin/extras/icons/libreelec.png</texture>\n'
    '            </control>\n'
    '            <control type="label">\n'
    '                <height>60</height>\n'
    '                <textcolor>main_fg_100</textcolor>\n'
    '                <label>LibreELEC</label>\n'
    '                <font>font_logo_xlarge</font>\n'
    '                <align>center</align>\n'
    '            </control>\n'
    '        </control>')
_AF3_LE_FONT = (
    '\n            <!-- ABK LibreELEC logo font -->\n'
    '            <font>\n'
    '                <name>font_logo_xlarge</name>\n'
    '                <filename>Questrial-Regular.ttf</filename>\n'
    '                <size>110</size>\n'
    '            </font>')

PATCHES += [
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes_Objects.xml'),
        'os': 'libreelec',
        'not_found_ok': True,
        'old': '', 'new': '',
        'already_patched_check': '<!-- ABK LibreELEC logo -->',
        # the FIRST grouplist of Object_StartUp_Logo (image + label)
        'fallback_pattern': _AF3_LOGO_RE,
        'fallback_repl': _AF3_LE_LOGO.replace('\\', '\\\\'),
        'regex_flags': re.S,
        'description': 'AF3 on LibreELEC - LibreELEC start-up logo',
    },
    {
        'addon_id': 'skin.arctic.fuse.3',
        'rel_path': os.path.join('1080i', 'Includes_Font.xml'),
        'os': 'libreelec',
        'not_found_ok': True,
        'old': '', 'new': '',
        'already_patched_check': '<!-- ABK LibreELEC logo font -->',
        'obsolete_if_contains': '<name>font_logo_xlarge</name>',
        'fallback_pattern': r'(<font>\s*<name>font_logo_large</name>.*?</font>)',
        'fallback_repl': r'\1' + _AF3_LE_FONT,
        'regex_flags': re.S,
        'description': 'AF3 on LibreELEC - font_logo_xlarge for the logo',
    },
]


# ── Arctic Fuse 3: one skin (Piers repo) for every platform (3.4.18) ──
# All three skins.json now install the SAME AF3 from taiseer999Piers.github.io
# (its start-up logo says CoreELEC "NO" = Piers / Kodi 22). On a Kodi 21.3 or a
# CoreELEC 21.3 "NG" box the two platform-specific bits are put back:
#   * Includes_Objects.xml Object_StartUp_Logo  -> kodi.png + KODI  /
#                                                  CE.png + CoreELEC "NG"
#   * extras/profiles/Mountains (1).jpg         -> Kodi / CoreELEC picture
# The logo is a TARGETED edit, not the supplied whole Includes_Objects.xml:
# those copies predate AF3 50.11.9 and would delete Object_StatisticsDots_Month
# (verified against the Piers repo source 2026-10-21) - the logo block is the
# only platform difference between them. 'platform' gate = _platform_id():
# 'kodi21' (not CoreELEC/LibreELEC, Kodi 21), 'coreelec21' (CoreELEC, Kodi 21),
# 3.4.19: 'kodi22' / 'coreelec22' (Kodi 22 and newer, e.g. 23 alpha) get the
# splash logo too - plain Kodi shows KODI, CoreELEC shows CoreELEC "NO"; the
# Mountains picture stays the skin's own Kodi 22 one there. LibreELEC (21 and
# 22) keeps its own logo patch above, which is not version-gated.
def _af3_logo_block(tag, icon, label):
    return (
        '<include name="Object_StartUp_Logo">\n'
        '        <!-- ABK %s logo -->\n'
        '        <control type="grouplist">\n'
        '            <height>128</height>\n'
        '            <centertop>350</centertop>\n'
        '            <orientation>vertical</orientation>\n'
        '            <align>center</align>\n'
        '            <control type="image">\n'
        '                <width>96</width>\n'
        '                <height>96</height>\n'
        '                <centerleft>50%%</centerleft>\n'
        '                <aspectratio>keep</aspectratio>\n'
        '                <texture>special://skin/extras/icons/%s</texture>\n'
        '            </control>\n'
        '            <control type="label">\n'
        '                <height>30</height>\n'
        '                <textcolor>main_fg_100</textcolor>\n'
        '                <label>%s</label>\n'
        '                <font>font_logo_large</font>\n'
        '                <align>center</align>\n'
        '            </control>\n'
        '        </control>') % (tag, icon, label)


_AF3_PLATFORMS = (
    # platform id,  sentinel tag,   icon,       label,               asset folder
    ('kodi21',     'Kodi 21',      'kodi.png', 'KODI',              'kodi21'),
    ('coreelec21', 'CoreELEC NG',  'CE.png',   'CoreELEC "NG"',     'coreelec21'),
    ('kodi22',     'Kodi 22',      'kodi.png', 'KODI',              None),
    ('coreelec22', 'CoreELEC NO',  'CE.png',   'CoreELEC "NO"',     None),
)

for _pid, _tag, _icon, _label, _dir in _AF3_PLATFORMS:
    PATCHES += [
        {
            'addon_id': 'skin.arctic.fuse.3',
            'rel_path': os.path.join('1080i', 'Includes_Objects.xml'),
            'platform': _pid,
            'not_found_ok': True,
            'old': '', 'new': '',
            'already_patched_check': '<!-- ABK %s logo -->' % _tag,
            # the FIRST grouplist of Object_StartUp_Logo (image + label)
            'fallback_pattern': _AF3_LOGO_RE,
            'fallback_repl': _af3_logo_block(_tag, _icon, _label).replace('\\', '\\\\'),
            'regex_flags': re.S,
            'description': 'AF3 on %s - %s start-up logo' % (_tag, _label),
        },
    ]
    if _dir:
        PATCHES += [
        {
            'addon_id': 'skin.arctic.fuse.3',
            'rel_path': os.path.join('extras', 'profiles', 'Mountains (1).jpg'),
            'platform': _pid,
            'inject_file': True,
            'binary': True,
            'replace': True,
            'not_found_ok': True,
            'inject_source': os.path.join('resources', 'af3_platform', _dir,
                                          'Mountains (1).jpg'),
            'description': 'AF3 on %s - profile picture Mountains (1).jpg' % _tag,
        },
        ]


_SKINVARS_AR_FIX = (
    # id, Arabic (po-escaped: \n stays a literal backslash-n)
    ('32018', r'تمت إضافة\n[B]{}[/B]\nإلى\n[B]{}[/B]'),
    ('32025', r'أُضيف\n[B]{}[/B]\nبوصفه\n[B]{}[/B]'),
    ('32028', r'تم استيراد\n[B]{}[/B]\nإلى\n[B]{}[/B]'),
    ('32034', 'أدخل اسم تسمية المعلومات أو الخاصية المخصّصة لـ[LOWERCASE]{}[/LOWERCASE]'),
    ('32035', 'أدخل القيمة المخصّصة لـ[LOWERCASE]{}[/LOWERCASE] للمطابقة'),
    ('32036', 'أقل من <'),
    ('32037', 'أقل من أو يساوي <='),
    ('32038', 'يساوي =='),
    ('32039', 'لا يساوي !='),
    ('32040', 'أكبر من أو يساوي >='),
    ('32041', 'أكبر من >'),
    ('32043', '[COLOR=red][B]تحذير[/B][/COLOR]: لا يمكن التراجع عن هذا الإجراء.'),
    ('32084', '[B][COLOR=red]تحذير[/COLOR][/B]: ستُضيف هذه القائمة {item_count} '
              'عنصرًا جديدًا (مع تخطّي {skip_count} من العناصر المضافة سابقًا). '
              'لا يمكن التراجع عن هذا الإجراء.'),
)


def _skinvars_ar_entry(sid, ar):
    # sentinel: the msgctxt line is NOT in it (it never changes); the msgstr
    # up to the first escape is unique per entry and contains no backslash,
    # so it is a plain substring of both the output and fallback_repl.
    head = ar.split('\\')[0]
    sentinel = 'msgstr "%s%s' % (head, '"' if head == ar else '')
    return {
        'addon_id': 'script.skinvariables',
        'rel_path': os.path.join('resources', 'language', 'resource.language.ar_sa', 'strings.po'),
        'old': '',
        'new': '',
        'already_patched_check': sentinel,
        'fallback_pattern': (r'msgctxt "#%s"\r?\nmsgid ("[^\r\n]*")\r?\nmsg(?:id|str) "[^\r\n]*"' % sid),
        'fallback_repl': 'msgctxt "#%s"\nmsgid \\g<1>\nmsgstr "%s"' % (sid, ar.replace('\\', '\\\\')),
        'not_found_ok': True,
        'description': 'skinvariables ar_sa strings.po #%s - msgstr in MSA' % sid,
    }


PATCHES += [_skinvars_ar_entry(_sid, _ar) for _sid, _ar in _SKINVARS_AR_FIX]



# ── AB Scrapers support for Fenlight & Umbrella (3.4.16) ──
# script.module.abscrapers merges CocoScrapers + Gears + Magneto behind one
# magneto-style API (abscrapers.sources()). Two things kept it out:
#  1. Fenlight's import_external_scrapers() hard-requires
#     <module>.modules.control.getProviderDefaults(); when that import fails it
#     returns False and Fenlight drops ALL external scrapers ("Error Importing
#     External Module"). Made tolerant: modules.control -> <module>.common ->
#     no defaults (only affects the "default providers only" scrape mode).
#  2. With no external module chosen yet, both add-ons refuse to scrape
#     externals. If AB Scrapers is installed and nothing was chosen, they now
#     fall back to it. A module the user picked by hand always wins.
_ABS_FEN_DEFAULTS_OLD = (
    "\t\t\tself.provider_defaults = [k.split('.')[1] for k, v in manual_function_import("
    "'%s.modules.control' % self.ext_name, 'getProviderDefaults')().items() if v == 'true']")
_ABS_FEN_DEFAULTS_NEW = (
    "\t\t\t# -- AB Scrapers support (by ABUKARIM TOOLS) --\r\n"
    "\t\t\ttry: _abk_defaults = manual_function_import('%s.modules.control' % self.ext_name, 'getProviderDefaults')()\r\n"
    "\t\t\texcept Exception:\r\n"
    "\t\t\t\ttry: _abk_defaults = manual_function_import('%s.common' % self.ext_name, 'getProviderDefaults')()\r\n"
    "\t\t\t\texcept Exception: _abk_defaults = {}\r\n"
    "\t\t\tself.provider_defaults = [k.split('.')[1] for k, v in _abk_defaults.items() if v == 'true']")
_ABS_FEN_INFO_OLD = "\tif module in ('empty_setting', ''): return None, ''"
_ABS_FEN_INFO_NEW = (
    "\tif module in ('empty_setting', ''):\r\n"
    "\t\t# -- AB Scrapers default external module (by ABUKARIM TOOLS) --\r\n"
    "\t\tif __import__('xbmc').getCondVisibility('System.HasAddon(script.module.abscrapers)'): return 'script.module.abscrapers', 'abscrapers'\r\n"
    "\t\treturn None, ''")
_ABS_UMB_OLD = (
    "\t\t\tif getSetting('external_provider.module', '') == '':\r\n"
    "\t\t\t\t#no external_provider_module\r\n"
    "\t\t\t\tcontrol.notification(message=control.lang(40447))\r\n"
    "\t\t\t\tself.sourceDict = internalSources()\r\n"
    "\t\t\t\tself.sourceDict.extend(cloudSources())\r\n"
    "\t\t\telse:\r\n"
    "\t\t\t\ttry:\r\n"
    "\t\t\t\t\tfrom sys import path\r\n"
    "\t\t\t\t\tpath.append(control.transPath('special://home/addons/%s/lib' % getSetting('external_provider.module', '')))\r\n"
    "\t\t\t\t\tfrom importlib import import_module\r\n"
    "\t\t\t\t\tfs_sources = getattr(import_module(getSetting('external_provider.name')), 'sources')\r\n")
_ABS_UMB_NEW = (
    "\t\t\t# -- AB Scrapers default external module (by ABUKARIM TOOLS) --\r\n"
    "\t\t\t_abk_mod, _abk_name = getSetting('external_provider.module', ''), getSetting('external_provider.name')\r\n"
    "\t\t\tif _abk_mod == '' and control.condVisibility('System.HasAddon(script.module.abscrapers)'): _abk_mod, _abk_name = 'script.module.abscrapers', 'abscrapers'\r\n"
    "\t\t\tif _abk_mod == '':\r\n"
    "\t\t\t\t#no external_provider_module\r\n"
    "\t\t\t\tcontrol.notification(message=control.lang(40447))\r\n"
    "\t\t\t\tself.sourceDict = internalSources()\r\n"
    "\t\t\t\tself.sourceDict.extend(cloudSources())\r\n"
    "\t\t\telse:\r\n"
    "\t\t\t\ttry:\r\n"
    "\t\t\t\t\tfrom sys import path\r\n"
    "\t\t\t\t\tpath.append(control.transPath('special://home/addons/%s/lib' % _abk_mod))\r\n"
    "\t\t\t\t\tfrom importlib import import_module\r\n"
    "\t\t\t\t\tfs_sources = getattr(import_module(_abk_name), 'sources')\r\n")

PATCHES += [
    {
        'addon_id': 'plugin.video.fenlight',
        'rel_path': os.path.join('resources', 'lib', 'modules', 'sources.py'),
        'toggle': 'abscrapers_support',
        'old': _ABS_FEN_DEFAULTS_OLD,
        'new': _ABS_FEN_DEFAULTS_NEW,
        'already_patched_check': '# -- AB Scrapers support (by ABUKARIM TOOLS) --',
        'fallback_pattern': (r"\t\t\tself\.provider_defaults = \[k\.split\('\.'\)\[1\] for k, v in "
                             r"manual_function_import\('%s\.modules\.control' % self\.ext_name, "
                             r"'getProviderDefaults'\)\(\)\.items\(\) if v == 'true'\]"),
        'fallback_repl': lambda _m: _ABS_FEN_DEFAULTS_NEW,
        'description': 'Fenlight sources.py - external module without modules.control (AB Scrapers) no longer disables external scrapers',
    },
    {
        'addon_id': 'plugin.video.fenlight',
        'rel_path': os.path.join('resources', 'lib', 'modules', 'settings.py'),
        'toggle': 'abscrapers_support',
        'old': _ABS_FEN_INFO_OLD,
        'new': _ABS_FEN_INFO_NEW,
        'already_patched_check': '# -- AB Scrapers default external module (by ABUKARIM TOOLS) --',
        'description': 'Fenlight settings.py - use AB Scrapers when no external module is chosen',
    },
    {
        'addon_id': 'plugin.video.umbrella',
        'rel_path': os.path.join('resources', 'lib', 'modules', 'sources.py'),
        'toggle': 'abscrapers_support',
        'not_found_ok': True,
        'old': _ABS_UMB_OLD,
        'new': _ABS_UMB_NEW,
        'already_patched_check': '# -- AB Scrapers default external module (by ABUKARIM TOOLS) --',
        'description': 'Umbrella sources.py - use AB Scrapers when no external module is chosen',
    },
]


# ── DexHub: Plugin Entry Fix (3.4.26, toggle 'dexhub_entry') ──
# Kodi 22 beta1 runs DexHub's xbmc.ui.screensaver library (screensaver.py)
# for plugin:// calls - kodi.log 2026-10-24: every Home widget / menu call
# (continue, nextup, emby_menu, silo_menu, providers) logged "Kodi ran the
# screensaver entry ... handed to default.py" and the invokers then sat in
# "waiting on thread". DexHub's own redirect hides the crash but not the
# misroute. Commenting the screensaver extension out of addon.xml leaves
# pluginsource as DexHub's only script entry, so Kodi has nothing else to
# pick. Cost: Dex Hub is no longer offered as a screensaver. Kodi reads
# addon.xml on UpdateLocalAddons, fired after the write ('rescan_addons').
# Toggle off -> revert_when_off restores the stock line.
_DEXHUB_SS_STOCK = '<extension point="xbmc.ui.screensaver" library="screensaver.py" />'
_DEXHUB_SS_OFF = ('<!-- ABK dexhub-ss-off: <extension point="xbmc.ui.screensaver" '
                  'library="screensaver.py" /> -->')

PATCHES += [
    {
        'addon_id': 'plugin.video.dexhub',
        'rel_path': 'addon.xml',
        'toggle': 'dexhub_entry',
        'old': _DEXHUB_SS_STOCK,
        'new': _DEXHUB_SS_OFF,
        'already_patched_check': 'ABK dexhub-ss-off',
        'fallback_pattern': r'<extension\s+point=["\']xbmc\.ui\.screensaver["\'][^>]*?/>',
        'fallback_repl': lambda _m: '<!-- ABK dexhub-ss-off: ' + _m.group(0) + ' -->',
        'revert_when_off': (_DEXHUB_SS_OFF, _DEXHUB_SS_STOCK),
        'rescan_addons': True,
        'not_found_ok': True,
        'description': 'DexHub addon.xml - screensaver extension off (Kodi 22 ran screensaver.py for plugin:// calls)',
    },
]


def _restart_addon(addon_id):
    """Disable + re-enable an add-on so a patched xbmc.service reloads now."""
    import json as _json
    for flag in (False, True):
        try:
            xbmc.executeJSONRPC(_json.dumps({'jsonrpc': '2.0', 'id': 1,
                                             'method': 'Addons.SetAddonEnabled',
                                             'params': {'addonid': addon_id, 'enabled': flag}}))
        except Exception:
            pass
        xbmc.sleep(500)

# ---------------------------------------------------------------------------
def _log(msg, level=None):
    xbmc.log('[AbukarimTools Patcher] %s' % msg,
             xbmc.LOGINFO if level is None else level)


def _trace(msg):
    xbmc.log('[AbukarimTools Trace] %s' % msg, xbmc.LOGDEBUG)


def _read(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


def _write(path, content):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)


def _audit_sentinels():
    """Warn about entries whose already_patched_check can never match their own output.

    A sentinel that is not a substring of what the entry writes means the patch can
    never recognise its own work: every sweep retries it, fails to find 'old' (it was
    already replaced), and reports a failure forever. That is exactly what the RedLight
    busy-player entry did once RedLight joined the automatic sweeps. Cheap enough to run
    on every pass, and it turns a silent permanent failure into one obvious log line.
    """
    for patch in PATCHES:
        sentinel = patch.get('already_patched_check')
        if not sentinel:
            continue
        written = patch.get('new') or ''
        if not written and isinstance(patch.get('fallback_repl'), str):
            written = patch['fallback_repl']
        if written and sentinel not in written:
            _log('SENTINEL BUG: %s - already_patched_check is not a substring of what '
                 'this entry writes, so it will re-run and fail on every sweep.'
                 % patch['rel_path'], xbmc.LOGWARNING)


def _apply_patch(patch):
    """
    Apply a single patch dict.
    Returns (success: bool, message: str)
    """
    # 3.2.7: "once" entries (remote) run a single time per box, then never
    # again - a whole-file replace must not keep reverting later edits.
    if patch.get('once'):
        from resources.lib import remote_patches
        if remote_patches.once_done(patch):
            return True, '[%s] Applied once already – skipping.' % patch['addon_id']
    # Resolve base dir: default is addons/, optionally addon_data/ for userdata targets.
    if patch.get('base') == 'addon_data':
        addon_path = os.path.join(ADDON_DATA, patch['addon_id'])
        # addon_data dir may not exist yet (addon never run); inject_file creates it.
        if not os.path.isdir(addon_path) and not patch.get('inject_file'):
            # Optional userdata target (e.g. a4kSubtitles never opened, so no
            # addon_data settings.xml yet): the addon default governs, so skip
            # cleanly instead of counting a failure.
            if patch.get('not_found_ok'):
                return True, '[%s] addon_data not present \u2013 skipping (optional).' % patch['addon_id']
            return False, '[%s] addon_data not found: %s' % (patch['addon_id'], addon_path)
    else:
        # Prefer Kodi's own registry: robust across platforms, portable installs,
        # and non-default addon directories (e.g. macOS test environments).
        addon_path = (_resolve_addon_dir(patch['addon_id'])
                      or os.path.join(ADDONS_DIR, patch['addon_id']))
        if not os.path.isdir(addon_path):
            # Optional target (e.g. a skin that may not be installed): skip
            # cleanly instead of counting a failure, so a toggle spanning two
            # addons doesn't report errors when only one is present.
            if patch.get('not_found_ok'):
                return True, '[%s] Addon not present – skipping (optional).' % patch['addon_id']
            return False, '[%s] Addon not found: %s' % (patch['addon_id'], addon_path)

    # Lucent theme entries are whole-feature installs handled by their own module.
    if patch.get('lucent'):
        from resources.lib import lucent_sources
        return lucent_sources.apply(addon_path, patch['lucent'])

    # Version window (remote entries, optional on built-ins): a patch written
    # for 3.4.x must never touch 3.5.0.
    if patch.get('min_version') or patch.get('max_version'):
        from resources.lib import remote_patches
        ok_v, ver = remote_patches.version_ok(patch, addon_path)
        if not ok_v:
            return True, ('[%s] Version %s outside %s..%s – patch not applicable, '
                          'skipping.' % (patch['addon_id'], ver,
                                         patch.get('min_version') or '*',
                                         patch.get('max_version') or '*'))

    # skip_if_present: the upstream add-on has since shipped the feature this
    # patch used to inject, so the patch is obsolete on this build. When the
    # named file exists inside the add-on, treat the patch as already satisfied
    # and skip cleanly (not a failure) instead of hunting for a match string
    # that no longer exists. Example: Seren 3.4.25+ ships native Trakt QR auth
    # (resources/skins/Default/1080i/qr_auth_window.xml), replacing our
    # trakt.py injection entirely.
    for rel in (patch.get('skip_if_present') or ()):
        if os.path.isfile(os.path.join(addon_path, rel)):
            return True, ('[%s] Native support present (%s) – patch obsolete, '
                          'skipping.' % (patch['addon_id'], rel))

    # Resolve target: support a list of candidate paths (rel_path_alternates)
    # so a single entry can cover multiple upstream file layouts.  When a list
    # is given, use the first candidate whose file exists; when none exist,
    # fall back to the primary rel_path so the "not found" error still names
    # the primary location.
    candidates = list(patch.get('rel_path_alternates') or ())
    candidates.insert(0, patch['rel_path'])
    target = None
    for cand in candidates:
        c = os.path.join(addon_path, cand)
        if os.path.isfile(c):
            target = c
            break
    if target is None:
        target = os.path.join(addon_path, patch['rel_path'])
    # 3.2.6: structured JSON edits (remote patches.json "json_edit") - match
    # items by key instead of text, so formatting differences don't matter.
    if patch.get('json_edit'):
        from resources.lib import remote_patches
        return remote_patches.apply_json_edit(patch, target)
    # inject_file: ينشئ الملف مباشرة قبل أي فحص
    if patch.get('inject_file'):
        b64 = patch.get('inject_content_b64', '')
        # Binary payloads (e.g. PNG textures) must be written as raw bytes.
        # Source is either an inline base64 blob (inject_content_b64) or, for
        # large assets, a file shipped inside this add-on (inject_source, a path
        # relative to the add-on root) so patcher.py stays readable.
        if patch.get('binary'):
            src_rel = patch.get('inject_source')
            if src_rel:
                src_abs = os.path.join(
                    xbmcvfs.translatePath('special://home/addons/'
                                          'plugin.program.abukarimtools/'),
                    src_rel)
                try:
                    with open(src_abs, 'rb') as _sf:
                        payload = _sf.read()
                except Exception as e:
                    return False, ('[%s] Source asset missing (%s): %s'
                                   % (patch['addon_id'], src_rel, e))
            else:
                payload = base64.b64decode(b64)
            # Idempotent replacement: if the target already holds exactly this
            # payload, skip (so the watchdog doesn't rewrite it every sweep).
            # 'replace' patches overwrite differing content; without 'replace'
            # an existing non-empty file is left as-is (create-only behaviour).
            if os.path.isfile(target):
                try:
                    with open(target, 'rb') as _cur:
                        current = _cur.read()
                except Exception:
                    current = None
                if current == payload:
                    return True, '[%s] Already present – skipping.' % patch['addon_id']
                if not patch.get('replace') and current:
                    return True, '[%s] Already present – skipping.' % patch['addon_id']
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, 'wb') as _bf:
                _bf.write(payload)
            if patch.get('restart_addon'):
                _restart_addon(patch['addon_id'])
            return True, '[%s] File injected OK: %s' % (patch['addon_id'], patch['description'])
        inject_content = base64.b64decode(b64).decode('utf-8') if b64 else patch.get('inject_content', '')
        already_check = patch.get('already_patched_check', '')
        if os.path.isfile(target) and already_check and already_check in _read(target):
            return True, '[%s] Already patched – skipping.' % patch['addon_id']
        # Sentinel-less injections (the player JSONs, trakt_auth_qr.xml) used to be
        # rewritten on EVERY pass, so each sweep reported "4 written" and the watchdog
        # popped "Patches re-applied after add-on update" every 30 minutes even though
        # nothing had changed. Compare the content instead: identical file, nothing to do.
        if os.path.isfile(target) and _read(target) == inject_content:
            return True, '[%s] Already patched – skipping.' % patch['addon_id']
        os.makedirs(os.path.dirname(target), exist_ok=True)
        _write(target, inject_content)
        return True, '[%s] File injected OK: %s' % (patch['addon_id'], patch['description'])

    if not os.path.isfile(target):
        return False, '[%s] Target file not found: %s' % (patch['addon_id'], patch['rel_path'])

    content = _read(target)

    # Check if already patched — use explicit sentinel if provided, else 'new' string
    already_check = patch.get('already_patched_check', patch['new'])
    if already_check is not None and already_check in content:
        return True, '[%s] Already patched – skipping.' % patch['addon_id']

    # target_sha256: the entry was written against specific upstream file(s).
    # Any other content means upstream changed it - stay out (not a failure).
    if patch.get('target_sha256'):
        from resources.lib import remote_patches
        if not remote_patches.sha_ok(patch, target):
            return True, ('[%s] %s changed upstream (sha256 mismatch) – patch '
                          'not applicable, skipping.' % (patch['addon_id'], patch['rel_path']))

    # obsolete_if_contains: upstream has since fixed this itself, so the file no
    # longer contains our 'old' anchor and never will. Unlike skip_if_present
    # (which keys on a file existing), this keys on a marker string inside the
    # target file — the fingerprint of the upstream fix. When present, the patch
    # is obsolete on this build: skip cleanly instead of reporting a permanent
    # "Patch string not found" failure on every sweep. Example: TMDbHelper
    # rewrote trakt_stats.py get_items() with its own recursive dict/int guard,
    # replacing our dict-guard comprehension patch entirely.
    obsolete_markers = patch.get('obsolete_if_contains')
    if obsolete_markers:
        if isinstance(obsolete_markers, str):
            obsolete_markers = (obsolete_markers,)
        if all(m in content for m in obsolete_markers):
            return True, ('[%s] Upstream fix present in %s – patch obsolete, '
                          'skipping.' % (patch['addon_id'], patch['rel_path']))

    # Exact match replacement (skip when old is empty, e.g. regex-only entries)
    if patch['old'] and patch['old'] in content:
        content = content.replace(patch['old'], patch['new'], 1)
        _write(target, content)
        return True, '[%s] Patched OK: %s' % (patch['addon_id'], patch['description'])

    # Exact match – CRLF normalised
    content_lf = content.replace('\r\n', '\n')
    old_lf = patch['old'].replace('\r\n', '\n')
    if old_lf and old_lf in content_lf:
        patched = content_lf.replace(old_lf, patch['new'].replace('\r\n', '\n'), 1)
        _write(target, patched)
        return True, '[%s] Patched OK (LF): %s' % (patch['addon_id'], patch['description'])

    # Fallback: regex replacement
    pattern = patch.get('fallback_pattern')
    repl    = patch.get('fallback_repl')
    if pattern and repl:
        _count = patch.get('count', 1)
        # No re.DOTALL by default (3.1.0.15): patterns that must cross lines
        # say so explicitly with [\s\S] / \n. DOTALL turned '.*' into a
        # multi-line wildcard, which is what made the TinyPPI fonts.py pattern
        # backtrack exponentially and freeze Kodi. An entry can still opt in
        # with 'regex_flags': re.DOTALL.
        new_content, n = re.subn(pattern, repl, content, count=_count,
                                 flags=patch.get('regex_flags', 0))
        if n:
            _write(target, new_content)
            return True, '[%s] Patched OK (regex): %s' % (patch['addon_id'], patch['description'])

    if patch.get('not_found_ok'):
        return True, '[%s] Already patched – skipping.' % patch['addon_id']

    return False, '[%s] Patch string not found in %s' % (patch['addon_id'], patch['rel_path'])


# ---------------------------------------------------------------------------
# Toggle groups
# ---------------------------------------------------------------------------
# Patches are grouped into a small number of user-facing TOGGLES. The user
# picks which toggles to apply from a checklist shown at the start of the
# "Apply Patches" run (the toggle step is a mandatory pre-step to patching —
# there is no separate menu item). Their choice is persisted to addon_data as a
# JSON list of DISABLED toggle ids (storing the disabled set means a toggle
# added in a future build defaults to ENABLED without the user re-ticking it).
#
# Each patch is mapped to a toggle by (addon_id, rel_path) in _TOGGLE_OF below.
# Patches NOT in that map have no toggle: they would be ALWAYS-ON fixes that
# apply on every run regardless of the checklist and are never shown as toggles.
# (Currently every patch belongs to a toggle, so there are none; the mechanism
# stays so a future always-on fix can be added just by omitting it from the map.)
#
# Every apply path — "Apply Patches" and the auto-patch watchdog — funnels
# through _select(), which drops patches whose toggle is disabled, so a toggle
# the user turned off stays off everywhere, including after an add-on update
# re-triggers the watchdog.

import json

# Ordered list of (toggle_id, display label). Order = order shown in the dialog.
TOGGLE_GROUPS = [
    ('tmdbh_trakt_auth', 'TMDbHelper Trakt Auth QR'),
    ('tmdbh_mpaa_ksa',   'MPAA for KSA'),
    ('tmdbh_stability',  'TMDbHelper: Stability'),
    ('tmdbh_genre_lang', 'TMDbHelper: Genres Follow Language'),
    ('tinyppi_codecs',   'TinyPPI: Codec Badges'),
    ('tinyppi_audio',    'TinyPPI: Audio Badges'),
    ('tinyppi_arabic',   'PPI Arabic'),
    ('ppi_af3',          'PPI AF3 Dialog (native)'),
    ('af3_vplot',        'AF3: Vertical Plot (Home, OSD & Views)'),
    ('af3_highlight',    'AF3: Highlight Genre & Widget Titles'),
    ('redlight_fixes',   'RedLight: Fix Sound & Theme'),
    ('fenlight_volume',  'Fenlight: Kill Volume Auto-Drop'),
    ('fenlight_tmdbh',   'Fenlight: TMDbHelper Playback Fix'),
    ('abscrapers_support', 'AB Scrapers: Fenlight & Umbrella Support'),
    ('a4ksubs_utf8',     'a4kSubtitles: UTF-8 Subtitles Fix'),
    ('a4ksubs_quiet',    'a4kSubtitles: Hide Account/API-Key Nags'),
    ('af3_subtools',     'AF3: Subtitle Buttons (DexSubtitles Sync & Cycler)'),
    ('af3_substyle',     'AF3: Subtitle Look Button (Dex Hub look: font, size, colour, delay, sync...)'),
    ('dexhub_entry',     'DexHub: Plugin Entry Fix (Kodi 22)'),
]
_TOGGLE_LABELS = dict(TOGGLE_GROUPS)

# (addon_id, rel_path) -> toggle_id. rel_path uses os.path.join so it matches
# the same construction in PATCHES on every platform. Any patch not listed here
# is always-on (no toggle).
_TOGGLE_OF = {
    # TMDbHelper Trakt Auth QR — the four QR entries
    ('plugin.video.themoviedb.helper',
     os.path.join('resources', 'tmdbhelper', 'lib', 'api', 'trakt', 'qr_utils.py')):      'tmdbh_trakt_auth',
    ('plugin.video.themoviedb.helper',
     os.path.join('resources', 'skins', 'Default', '1080i', 'trakt_auth_qr.xml')):        'tmdbh_trakt_auth',
    ('plugin.video.themoviedb.helper',
     os.path.join('resources', 'skins', 'Default', 'media', 'white.png')):                'tmdbh_trakt_auth',
    ('plugin.video.themoviedb.helper',
     os.path.join('resources', 'tmdbhelper', 'lib', 'api', 'trakt', 'authenticator.py')): 'tmdbh_trakt_auth',
    # MPAA for KSA — the certification fallback
    ('plugin.video.themoviedb.helper',
     os.path.join('resources', 'tmdbhelper', 'lib', 'items', 'database',
                  'basemeta_factories', 'concrete_classes', 'info.py')):     'tmdbh_mpaa_ksa',
    # TMDbHelper: Stability — dead-player guard (getPlayingFile RuntimeError on teardown)
    ('plugin.video.themoviedb.helper',
     os.path.join('resources', 'tmdbhelper', 'lib', 'monitor', 'player.py')): 'tmdbh_stability',
    # TinyPPI: Codec Badges — the three HDR badge PNGs
    ('script.tinyppi',
     os.path.join('resources', 'skins', 'Default', 'media', 'codecs', 'SDR.png')):        'tinyppi_codecs',
    ('script.tinyppi',
     os.path.join('resources', 'skins', 'Default', 'media', 'codecs', 'HDR10.png')):      'tinyppi_codecs',
    ('script.tinyppi',
     os.path.join('resources', 'skins', 'Default', 'media', 'codecs', 'HDR10Plus.png')):  'tinyppi_codecs',
    # TinyPPI: Audio Badges — the five Dolby audio badges
    ('script.tinyppi',
     os.path.join('resources', 'skins', 'Default', 'media', 'codecs', 'Dolby_Digital.png')):             'tinyppi_audio',
    ('script.tinyppi',
     os.path.join('resources', 'skins', 'Default', 'media', 'codecs', 'Dolby_Digital_Plus.png')):        'tinyppi_audio',
    ('script.tinyppi',
     os.path.join('resources', 'skins', 'Default', 'media', 'codecs', 'Dolby_Digital_Plus_Atmos.png')):  'tinyppi_audio',
    ('script.tinyppi',
     os.path.join('resources', 'skins', 'Default', 'media', 'codecs', 'Dolby_TrueHD.png')):               'tinyppi_audio',
    ('script.tinyppi',
     os.path.join('resources', 'skins', 'Default', 'media', 'codecs', 'Dolby_TrueHD_Atmos.png')):         'tinyppi_audio',
    # Fenlight: Kill Volume Auto-Drop
    ('plugin.video.fenlight',
     os.path.join('resources', 'lib', 'modules', 'kodi_utils.py')):          'fenlight_volume',
    # RedLight: Fix Sound & Theme — all three RedLight entries
    ('plugin.video.redlight',
     os.path.join('resources', 'lib', 'modules', 'kodi_utils.py')):          'redlight_fixes',
    ('plugin.video.redlight',
     os.path.join('resources', 'skins', 'Default', '1080i', 'sources_results.xml')): 'redlight_fixes',
    # a4kSubtitles: UTF-8 Subtitles Fix
    ('service.subtitles.a4ksubtitles',
     os.path.join('a4kSubtitles', 'download.py')):                           'a4ksubs_utf8',
}

_SELECTION_FILE = os.path.join(
    ADDON_DATA, 'plugin.program.abukarimtools', 'patch_toggles.json')


def _toggle_of(patch):
    """Return the toggle id for a patch, or None if it is an always-on fix.

    An explicit ``'toggle'`` on the entry wins, so two entries that share the
    same (addon_id, rel_path) — e.g. the PPI Arabic and classic PPI whole-file
    replacements of script-tinyppi-main.xml — can each carry their own toggle
    (the (addon_id, rel_path) map below can only hold one value per path).
    Legacy entries with no 'toggle' fall back to the path map.
    """
    if patch.get('toggle'):
        return patch['toggle']
    return _TOGGLE_OF.get((patch['addon_id'], patch.get('rel_path', '')))


def _all_patches():
    """Built-in PATCHES merged with abukarim/patches.json (cached, no network).

    Remote entries can add patches and kill built-ins (see remote_patches.py);
    any problem there falls back to the built-in list unchanged.
    """
    try:
        from resources.lib import remote_patches
        return remote_patches.merged(PATCHES, _toggle_of)
    except Exception as e:
        _log('remote patch merge failed (built-ins only): %s' % e, xbmc.LOGWARNING)
        return list(PATCHES)


def _toggle_groups():
    groups = list(TOGGLE_GROUPS)
    try:
        from resources.lib import remote_patches
        known = {t for t, _l in groups}
        groups += [(t, l) for t, l in remote_patches.extra_toggles() if t not in known]
    except Exception:
        pass
    return groups


def _load_disabled():
    """Return the set of disabled TOGGLE ids (empty set on any problem)."""
    try:
        with open(_SELECTION_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, list):
            return set(data)
    except Exception:
        pass
    return set()


def _save_disabled(disabled_toggles):
    """Persist the disabled-toggle set. Best-effort; never raises."""
    try:
        os.makedirs(os.path.dirname(_SELECTION_FILE), exist_ok=True)
        with open(_SELECTION_FILE, 'w', encoding='utf-8') as f:
            json.dump(sorted(disabled_toggles), f, indent=2)
        return True
    except Exception as e:
        _log('Could not save patch toggles: %s' % e, xbmc.LOGWARNING)
        return False


def _feature_on(name):
    """Is a Toggles-menu feature switched on? Unknown features count as off."""
    if name.startswith('lucent_'):
        try:
            from resources.lib import lucent_toggle
            return lucent_toggle.enabled(name[len('lucent_'):])
        except Exception:
            return False
    if name == 'ab_search':
        try:
            from resources.lib import lucent_toggle
            return lucent_toggle.search_on()
        except Exception:
            return False
    if name == 'af3_trailers':
        try:
            from resources.lib.af3_trailers import config as _trailers_config
            return _trailers_config.load().get('enabled', False)
        except Exception:
            return False
    return False


_OS_ID = []


def _os_id():
    """'libreelec', 'coreelec', ... from /etc/os-release ID, '' elsewhere
    (desktop / Android). Cached."""
    if not _OS_ID:
        osid, text = '', ''
        try:
            with open('/etc/os-release', 'r', encoding='utf-8', errors='replace') as f:
                text = f.read()
            for line in text.splitlines():
                if line.startswith('ID='):
                    osid = line.split('=', 1)[1].strip().strip('"').lower()
                    break
        except Exception:
            pass
        # 3.4.3: community builds ("LibreELEC (community)", kodi.log
        # 2026-10-14 19:42) - trust NAME / any line too, not only ID
        low = text.lower()
        for known in ('libreelec', 'coreelec'):
            if osid != known and known in low and not (osid in ('libreelec', 'coreelec')):
                osid = known
        _OS_ID.append(osid)
        _log('OS id: %s' % (osid or 'other'))
    return _OS_ID[0]


_PLATFORM_ID = []


def _platform_id():
    """'kodi21', 'coreelec21', 'libreelec21', 'coreelec22', 'kodi22', ...:
    the OS family (_os_id(); anything else = plain 'kodi') + Kodi's major
    version from System.BuildVersion. Cached."""
    if not _PLATFORM_ID:
        osid = _os_id()
        fam = osid if osid in ('coreelec', 'libreelec') else 'kodi'
        try:
            major = int(re.match(r'\d+', xbmc.getInfoLabel('System.BuildVersion')).group(0))
        except Exception:
            major = 0
        # 3.4.19: Kodi 22 and every newer build (23 alpha ...) = the Piers
        # generation, so one 'kodi22' / 'coreelec22' tag covers them.
        if major > 22:
            major = 22
        _PLATFORM_ID.append('%s%d' % (fam, major))
        _log('Platform id: %s' % _PLATFORM_ID[0])
    return _PLATFORM_ID[0]


def _select(group=None, addon_ids=None, respect_selection=True):
    """Return the patch entries to apply, optionally narrowed to addon ids.

    Always-on fixes (no toggle) are always included. Grouped patches are
    included only when their toggle is enabled. When respect_selection is False
    the toggle filter is skipped (the full set is returned); the `group`
    parameter is kept for signature compatibility but is unused now that
    grouping is derived from _TOGGLE_OF rather than a per-entry 'group' key.
    """
    selected = _all_patches()
    if addon_ids:
        wanted   = set(addon_ids)
        selected = [p for p in selected if p['addon_id'] in wanted]
    # Feature-gated entries (e.g. the AF3 auto-trailers skin patch) apply only
    # while that feature is switched on from its Toggles menu entry.
    selected = [p for p in selected
                if not p.get('feature') or _feature_on(p['feature'])]
    # 3.4.2: OS-gated entries ('os': 'libreelec' / 'coreelec' / ...)
    selected = [p for p in selected if not p.get('os') or p['os'] == _os_id()]
    # 3.4.18: platform-gated entries ('platform': 'kodi21' / 'coreelec21' ...)
    selected = [p for p in selected if not p.get('platform')
                or _platform_id() in ((p['platform'],) if isinstance(p['platform'], str)
                                      else tuple(p['platform']))]
    if respect_selection:
        disabled = _load_disabled()
        if disabled:
            selected = [p for p in selected
                        if _toggle_of(p) is None or _toggle_of(p) not in disabled]
    # Supersede: when an ACTIVE entry declares 'supersedes', drop any other
    # still-selected entry that writes the SAME (addon_id, rel_path) and belongs
    # to one of the superseded toggles. This stops two whole-file 'replace'
    # entries for one file (classic PPI vs PPI Arabic on script-tinyppi-main.xml)
    # from thrashing each other every sweep — the superseding file already
    # contains the superseded one's edits.
    superseded = {}  # (addon_id, rel_path) -> set of toggle ids it supersedes
    for p in selected:
        for tid in p.get('supersedes', ()):
            key = (p['addon_id'], p.get('rel_path', ''))
            superseded.setdefault(key, set()).add(tid)
    if superseded:
        kept = []
        for p in selected:
            key = (p['addon_id'], p.get('rel_path', ''))
            losing = superseded.get(key)
            # Drop p only if it is the superseded party (its toggle is in the
            # set) AND it is not itself the superseding entry.
            if losing and not p.get('supersedes') and _toggle_of(p) in losing:
                continue
            kept.append(p)
        selected = kept
    return selected


def target_addon_ids(group=None):
    """Ordered, de-duplicated list of addon ids this patch group targets.

    Used by the auto-patch watchdog to know which addons to watch, so the
    watch list can never drift out of sync with PATCHES.
    """
    seen = []
    for patch in _all_patches():
        if patch.get('group') != group:
            continue
        if patch['addon_id'] not in seen:
            seen.append(patch['addon_id'])
    return seen


# ---------------------------------------------------------------------------
# TinyPPI Arabic language reconcile (tied to the 'tinyppi_arabic' toggle STATE)
# ---------------------------------------------------------------------------
# Unlike a normal PATCHES entry (which only ever ACTS when its toggle is ON and
# is silently skipped when OFF), the Arabic language folder must react to the
# toggle in BOTH directions: PPI Arabic ON keeps TinyPPI's Arabic UI; PPI Arabic
# OFF makes the overlay fall back to English. Kodi has no per-addon language
# override and the patcher has no delete op, so we neutralise the folder without
# removing it: when disabled we replace ar_sa/strings.po with a HEADER-ONLY .po
# (no msgctxt entries), so Kodi finds no Arabic translations and falls back to
# the English msgid for every string. The real Arabic file is kept alongside as
# strings.po.abk_arabic_bak and restored verbatim when PPI Arabic is switched
# back on. Both directions are content-compared, so a settled box rewrites
# nothing and the watchdog stays quiet.
_TINYPPI_ARABIC_PO_REL = os.path.join(
    'resources', 'language', 'resource.language.ar_sa', 'strings.po')

# Header-only ar_sa strings.po: valid PO metadata, ZERO translated entries.
_TINYPPI_ARABIC_PO_EMPTY = (
    'msgid ""\n'
    'msgstr ""\n'
    '"MIME-Version: 1.0\\n"\n'
    '"Content-Type: text/plain; charset=UTF-8\\n"\n'
    '"Content-Transfer-Encoding: 8bit\\n"\n'
    '"X-Generator: POEditor.com\\n"\n'
    '"Project-Id-Version: TinyPPI\\n"\n'
    '"Language: ar\\n"\n'
    '\n'
    '# -- TinyPPI Arabic disabled by ABUKARIM TOOLS (PPI Arabic toggle OFF) --\n'
    '# Original Arabic translation preserved as strings.po.abk_arabic_bak;\n'
    '# re-enable the PPI Arabic toggle and re-run Apply Patches to restore it.\n'
)


_PO_ENTRY_RE = re.compile(r'msgctxt "#(\d+)"\s*\nmsgid "((?:[^"\\]|\\.)*)"')


def _po_ids(text):
    """{string id: English msgid} for a TinyPPI strings.po."""
    try:
        return dict(_PO_ENTRY_RE.findall(text or ''))
    except Exception:
        return {}


def _tinyppi_po_is_stale(ar_text, en_text):
    """3.2.39: True when an Arabic strings.po belongs to ANOTHER TinyPPI version.

    Every translated entry carries the English msgid; in a matching file it is
    the same as en_gb's for that id. A 2.11-era file on 2.15.0 has different
    texts on the same ids (32218 'Video' became a settings help line), which is
    what scrambled the overlay labels. Compared on the shared ids; >10 %
    mismatching = stale. Unknown/unparseable -> not stale (never act blind).
    """
    ar, en = _po_ids(ar_text), _po_ids(en_text)
    shared = [k for k in ar if k in en]
    if len(shared) < 20:
        return False
    bad = sum(1 for k in shared if ar[k] != en[k])
    return bad * 10 > len(shared)


def _reconcile_tinyppi_arabic():
    """Enforce the ar_sa strings.po state that matches the tinyppi_arabic toggle.

    Returns (ok, msg) using the same shape as _apply_patch so apply_set can fold
    it into its counters. Never raises: a problem here must not abort the sweep.
    """
    addon_id = 'script.tinyppi'
    # Resolve TinyPPI's path the same way _apply_patch does (registry first).
    addon_path = (_resolve_addon_dir(addon_id)
                  or os.path.join(ADDONS_DIR, addon_id))
    if not os.path.isdir(addon_path):
        return True, '[%s] Addon not present – skipping (optional).' % addon_id

    po_path  = os.path.join(addon_path, _TINYPPI_ARABIC_PO_REL)
    bak_path = po_path + '.abk_arabic_bak'
    en_path  = os.path.join(addon_path, 'resources', 'language',
                            'resource.language.en_gb', 'strings.po')
    arabic_disabled = 'tinyppi_arabic' in _load_disabled()
    try:
        en_text = _read(en_path) if os.path.isfile(en_path) else ''
    except Exception:
        en_text = ''

    try:
        if arabic_disabled:
            # Back up the genuine Arabic file once (only if the current file is
            # NOT already our header-only stub), then write the stub.
            current = None
            if os.path.isfile(po_path):
                try:
                    current = _read(po_path)
                except Exception:
                    current = None
            if current == _TINYPPI_ARABIC_PO_EMPTY:
                return True, '[%s] Arabic already disabled – skipping.' % addon_id
            # 3.2.39: ALWAYS refresh the backup from a real (non-stub) file.
            # It used to be written only once, so a TinyPPI update made while
            # Arabic was OFF left the 2.11 backup in place; switching Arabic
            # back ON then restored that 2.11 file over 2.15.0 (labels shown
            # as random settings texts). A stale live file is not backed up.
            if current is not None and not _tinyppi_po_is_stale(current, en_text):
                _write(bak_path, current)
            os.makedirs(os.path.dirname(po_path), exist_ok=True)
            _write(po_path, _TINYPPI_ARABIC_PO_EMPTY)
            return True, ('[%s] Patched OK: TinyPPI Arabic disabled '
                          '(en fallback; original backed up).' % addon_id)
        else:
            # PPI Arabic ON: restore the real Arabic file from backup if we have
            # one and the live file is still our stub.
            current = _read(po_path) if os.path.isfile(po_path) else None
            # 3.2.39 self-heal: a live Arabic file from another TinyPPI version
            # (restored by <=3.2.38) scrambles every label. Neutralise it with
            # the stub so the overlay is clean English until TinyPPI is
            # reinstalled/updated and ships its own matching Arabic file.
            if (current is not None and current != _TINYPPI_ARABIC_PO_EMPTY
                    and _tinyppi_po_is_stale(current, en_text)):
                _write(po_path, _TINYPPI_ARABIC_PO_EMPTY)
                try:
                    if os.path.isfile(bak_path) and _tinyppi_po_is_stale(
                            _read(bak_path), en_text):
                        os.remove(bak_path)
                except OSError:
                    pass
                return True, ('[%s] Patched OK: stale Arabic strings.po (other '
                              'TinyPPI version) replaced by English fallback - '
                              'reinstall TinyPPI to get its Arabic back.' % addon_id)
            if not os.path.isfile(bak_path):
                return True, '[%s] Arabic active – nothing to restore.' % addon_id
            backup  = _read(bak_path)
            # 3.2.39: never restore a backup made for another TinyPPI version.
            if _tinyppi_po_is_stale(backup, en_text):
                try:
                    os.remove(bak_path)
                except OSError:
                    pass
                return True, ('[%s] Arabic backup is from another TinyPPI '
                              'version – dropped, not restored.' % addon_id)
            if current == backup:
                return True, '[%s] Arabic already restored – skipping.' % addon_id
            # 3.2.20: restore ONLY over our own empty stub (or a missing file).
            # A real Arabic file that differs is a newer TinyPPI translation -
            # the old backup must never replace it (log 2026-10-04 19:35: the
            # 2.11-era backup overwrote 2.15.0's strings). Drop the stale backup.
            if current is not None and current != _TINYPPI_ARABIC_PO_EMPTY:
                try:
                    os.remove(bak_path)
                except OSError:
                    pass
                return True, ('[%s] Arabic active (newer translation) – stale '
                              'backup dropped.' % addon_id)
            _write(po_path, backup)
            return True, ('[%s] Patched OK: TinyPPI Arabic restored '
                          'from backup.' % addon_id)
    except Exception as e:
        return False, '[%s] Arabic reconcile failed: %s' % (addon_id, e)


# ---------------------------------------------------------------------------
# TinyPPI: Arabic or English overlay (3.2.40)
# ---------------------------------------------------------------------------
# What the build wants from TinyPPI is exactly this, nothing more:
#   * PPI Arabic ON  -> Arabic strings, our Arabic font, labels without ':'
#   * PPI Arabic OFF -> TinyPPI's own English overlay, untouched
#   (+ the codec badge PNGs, ordinary PATCHES)
#
# The overlay XML has to change in BOTH directions, and a ':' that was removed
# cannot be put back by a regex (only 46 of 73 labels carry one), so every
# skin XML is derived from a pristine copy kept beside it:
#   <file>.abk_orig  - TinyPPI's own file, refreshed whenever the live file is
#                      not ours (fresh install / TinyPPI update)
#   live file        - Arabic ON : transform(orig) + marker comment
#                      Arabic OFF: orig, byte for byte
# Our files carry _PPI_AR_MARKER, so "not ours" is a plain substring test.
#
# The Arabic font is registered under OUR OWN names (abk_ppi_ar21/abk_ppi_ar32)
# in the active skin's Font.xml, so the skin's own font23_narrow/font32 are
# never touched; the overlay only switches to those names once they exist in
# every Font.xml of the active skin (otherwise it keeps TinyPPI's fonts).

_PPI_AR_MARKER = '<!-- ABUKARIM TOOLS: PPI Arabic -->'
_PPI_XML_DIR = os.path.join('resources', 'skins', 'Default', '1080i')
_PPI_XML_FILES = ('script-tinyppi-main.xml', 'script-tinyppi-dv-metadata.xml',
                  'script-tinyppi-dialog.xml', 'script-tinyppi-dialog-bar.xml',
                  'script-tinyppi-dialog-single.xml')
_PPI_AR_FONT_FILE = ('special://home/addons/plugin.program.abukarimtools/'
                     'resources/fonts/Noto-Regular.ttf')
_PPI_AR_FONTS = (('font23_narrow', 'abk_ppi_ar21', '21'),
                 ('font32',        'abk_ppi_ar32', '32'))
_PPI_COLON_RE = re.compile(
    r'(\$ADDON\[script\.tinyppi \d+\](?:\[/?[A-Z]+\])*):([ \t]*</label>)')


def _read_raw(path):
    """Text read that keeps the file's own line endings (no newline mapping)."""
    with open(path, 'r', encoding='utf-8', newline='') as f:
        return f.read()


def _write_raw(path, content):
    with open(path, 'w', encoding='utf-8', newline='') as f:
        f.write(content)


def _ppi_arabic_xml(orig, use_font):
    """Arabic version of one TinyPPI skin XML (from TinyPPI's own text)."""
    text = _PPI_COLON_RE.sub(r'\1\2', orig)
    if use_font:
        for old, new, _size in _PPI_AR_FONTS:
            text = text.replace('<font>%s</font>' % old, '<font>%s</font>' % new)
    m = re.match(r'\s*<\?xml[^>]*\?>[ \t]*\r?\n?', text)
    cut = m.end() if m else 0
    return text[:cut] + _PPI_AR_MARKER + '\n' + text[cut:]


def _unclassic(text):
    """Undo the retired 'classic PPI' token swap (<=3.2.39) on an old live file.

    Safe on any version: TinyPPI's own main overlay uses neither token."""
    text = re.sub(r'TinyPPI\.Dialog(BackgroundColor|HeaderColor|HeaderIconColor|'
                  r'LineColor|GlobalBackgroundColor)\b', r'TinyPPI.\1', text)
    return re.sub(r'background/dialog-bg-(start|end)\.png',
                  r'background/overlay-bg-\1.png', text)


def _skin_font_xmls():
    """Every Font.xml of the active skin (one per <res> folder), or []."""
    try:
        skin = os.path.normpath(xbmcvfs.translatePath('special://skin/'))
    except Exception:
        return []
    if not os.path.isdir(skin):
        return []
    found = []
    try:
        with open(os.path.join(skin, 'addon.xml'), 'rb') as f:
            ax = re.sub(r'<!--.*?-->', '', f.read().decode('utf-8', 'replace'), flags=re.S)
        for tag in re.findall(r'<res\b[^>]*>', ax, re.I):
            m = re.search(r"""\bfolder\s*=\s*(["'])(.*?)\1""", tag)
            if not m or not m.group(2).strip():
                continue
            folder = os.path.normpath(os.path.join(skin, m.group(2).strip()))
            if os.path.commonpath((skin, folder)) != skin or not os.path.isdir(folder):
                continue
            for name in sorted(os.listdir(folder)):
                path = os.path.join(folder, name)
                if name.lower() == 'font.xml' and os.path.isfile(path) and path not in found:
                    found.append(path)
    except Exception:
        pass
    return found


def _font_block_re(name):
    return re.compile(r'<font>\s*<name>\s*%s\s*</name>' % re.escape(name))


def _ensure_ppi_fonts():
    """Register abk_ppi_ar21/32 in every fontset of the active skin.

    Returns (all_present, wrote). Text edit like TinyPPI's own (no XML
    rewrite); a skin that cannot be written simply keeps TinyPPI's fonts.
    """
    paths = _skin_font_xmls()
    if not paths:
        return False, False
    all_present, wrote = True, False
    for path in paths:
        try:
            with open(path, 'rb') as f:
                text = f.read().decode('utf-8')
        except Exception:
            all_present = False
            continue
        nl = '\r\n' if '\r\n' in text else '\n'
        changed = False

        def _fix(m):
            nonlocal changed
            open_tag, inner, close_tag = m.group(1), m.group(2), m.group(3)
            add = ''
            for _old, name, size in _PPI_AR_FONTS:
                if not _font_block_re(name).search(inner):
                    add += ('%s        <font>%s            <name>%s</name>%s'
                            '            <filename>%s</filename>%s'
                            '            <size>%s</size>%s        </font>'
                            % (nl, nl, name, nl, _PPI_AR_FONT_FILE, nl, size, nl))
            if not add:
                return m.group(0)
            changed = True
            return open_tag + add + inner + close_tag

        new = re.sub(r'(<fontset\b[^>]*>)(.*?)(</fontset>)', _fix, text, flags=re.S)
        if not re.search(r'<fontset\b', text):
            all_present = False
            continue
        if changed:
            try:
                tmp = path + '.abk_tmp'
                with open(tmp, 'wb') as f:
                    f.write(new.encode('utf-8'))
                os.replace(tmp, path)
                wrote = True
                _log('PPI Arabic fonts registered in %s' % path)
            except Exception as e:
                _log('PPI Arabic fonts: cannot write %s: %s' % (path, e), xbmc.LOGWARNING)
                all_present = False
    return all_present, wrote


def _cleanup_retired_tinyppi(addon_path):
    """Remove what retired TinyPPI patches left in the add-on: the PPI AF3 Home
    publisher (home_publish.py + its monitor.py hook, <=3.2.39).

    _ALLOW_NON_COREELEC is deliberately NOT touched: the TinyPPI build on the
    ABUKARIM repos (for non-CE22 boxes) ships with it set to True."""
    out = []
    hp = os.path.join(addon_path, 'resources', 'lib', 'info', 'home_publish.py')
    if os.path.isfile(hp):
        try:
            os.remove(hp)
            out.append((True, '[script.tinyppi] Patched OK: retired PPI AF3 '
                              'home_publish.py removed.'))
        except OSError as e:
            out.append((False, '[script.tinyppi] could not remove home_publish.py: %s' % e))
    mon = os.path.join(addon_path, 'resources', 'lib', 'service', 'monitor.py')
    if os.path.isfile(mon):
        try:
            text = _read(mon)
            new = re.sub(r'\n[ \t]*# -- PPI AF3 Home publisher \(by ABUKARIM TOOLS\) --\n'
                         r'[ \t]*try:\n[ \t]*from info import home_publish.*?\n'
                         r'[ \t]*_abk_home_publish\.start\(monitor\)\n'
                         r'[ \t]*except Exception as _abk_exc:\n[^\n]*\n?',
                         '\n', text, flags=re.S)
            if new != text:
                _write(mon, new)
                out.append((True, '[script.tinyppi] Patched OK: retired PPI AF3 '
                                  'hook removed from monitor.py (restart Kodi).'))
        except Exception as e:
            out.append((False, '[script.tinyppi] monitor.py cleanup failed: %s' % e))
    return out


def _reconcile_tinyppi_xml(addon_path, arabic):
    """Put every TinyPPI skin XML in the Arabic or English state."""
    out = []
    use_font = False
    if arabic:
        use_font, wrote = _ensure_ppi_fonts()
        if wrote:
            _mark_skin_reload()     # Font.xml is read at skin load
            out.append((True, '[script.tinyppi] Patched OK: PPI Arabic fonts '
                              'registered in the active skin.'))
        if not use_font:
            _log('PPI Arabic: Arabic font not registered in the active skin - '
                 'overlay keeps TinyPPI fonts for now.', xbmc.LOGWARNING)
    for name in _PPI_XML_FILES:
        live = os.path.join(addon_path, _PPI_XML_DIR, name)
        orig = live + '.abk_orig'
        if not os.path.isfile(live):
            continue
        try:
            cur = _read_raw(live)
            if _PPI_AR_MARKER not in cur:
                # TinyPPI's own file (fresh install/update) - or a main overlay
                # edited in place by <=3.2.39, whose classic swap we undo here
                # (main only: the VS10 dialog files use Dialog* tokens natively).
                clean = _unclassic(cur) if name == 'script-tinyppi-main.xml' else cur
                if not os.path.isfile(orig) or _read_raw(orig) != clean:
                    _write_raw(orig, clean)
            elif not os.path.isfile(orig):
                # Ours, but the pristine copy is gone: rebuild it as well as we
                # can (':' cannot come back - reinstall TinyPPI for those).
                base = cur.replace(_PPI_AR_MARKER + '\n', '', 1)
                for old, new, _size in _PPI_AR_FONTS:
                    base = base.replace('<font>%s</font>' % new, '<font>%s</font>' % old)
                _write_raw(orig, base)
                _log('PPI Arabic: %s pristine copy rebuilt from the live file '
                     '(reinstall TinyPPI to get its label colons back).' % name,
                     xbmc.LOGWARNING)
            base = _read_raw(orig)
            want = _ppi_arabic_xml(base, use_font) if arabic else base
            if cur != want:
                _write_raw(live, want)
                out.append((True, '[script.tinyppi] Patched OK: %s -> %s.'
                                  % (name, 'Arabic' if arabic else 'English')))
        except Exception as e:
            out.append((False, '[script.tinyppi] %s reconcile failed: %s' % (name, e)))
    return out


def _reconcile_tinyppi():
    """One pass that leaves TinyPPI exactly in the PPI Arabic / English state.
    Returns a list of (ok, msg). Never raises."""
    results = []
    try:
        results.append(_reconcile_tinyppi_arabic())
        addon_path = (_resolve_addon_dir('script.tinyppi')
                      or os.path.join(ADDONS_DIR, 'script.tinyppi'))
        if not os.path.isdir(addon_path):
            return results
        arabic = 'tinyppi_arabic' not in _load_disabled()
        results += _reconcile_tinyppi_xml(addon_path, arabic)
        results += _cleanup_retired_tinyppi(addon_path)
    except Exception as e:
        results.append((False, '[script.tinyppi] reconcile failed: %s' % e))
    return results


# ---------------------------------------------------------------------------
# Automatic ReloadSkin (3.1.0.28)
# ---------------------------------------------------------------------------
# Kodi reads a skin's XML once, when the skin loads, so a patch written into the
# ACTIVE skin does nothing on screen until the skin is reloaded. When a write
# lands in the active skin, apply_set() drops a marker file; the callers (the
# manual "Apply Patches" run after its results dialog, the watchdog sweeps and
# the menu sweep) then call reload_skin_if_pending(), which fires ReloadSkin()
# only when it is safe: no first-run in progress, nothing playing, no modal
# dialog up. Otherwise the marker stays and the watchdog retries on its next
# poll. A marker file (not a module flag) because the service and the plugin
# run in separate interpreters.
_SKIN_RELOAD_MARKER = os.path.join(
    ADDON_DATA, 'plugin.program.abukarimtools', 'skin_reload.pending')
_FIRST_RUN_LOCK_FILE = os.path.join(
    ADDON_DATA, 'plugin.program.abukarimtools', 'first_run.lock')
_SV_DEFER_PROP = 'abk.skin_reload.sv_wait_since'   # Home window: shared by service + plugin
_SV_MAX_DEFER  = 300                                # s: never wait longer than this


def _is_active_skin(addon_id):
    try:
        return addon_id == xbmc.getSkinDir()
    except Exception:
        return False


def _mark_skin_reload():
    try:
        os.makedirs(os.path.dirname(_SKIN_RELOAD_MARKER), exist_ok=True)
        with open(_SKIN_RELOAD_MARKER, 'w') as f:
            f.write(xbmc.getSkinDir())
    except Exception as e:
        _log('Could not mark skin reload: %s' % e, xbmc.LOGWARNING)


def reload_skin_if_pending():
    """Fire ReloadSkin() if a patch wrote into the active skin and it is safe
    to do so now. Returns True if a reload was issued. Never raises."""
    try:
        if not os.path.exists(_SKIN_RELOAD_MARKER):
            return False
        try:
            with open(_SKIN_RELOAD_MARKER, 'r') as f:
                skin = f.read().strip()
        except Exception:
            skin = ''
        if skin and skin != xbmc.getSkinDir():
            # The user switched skins since; the new skin loaded fresh files.
            os.remove(_SKIN_RELOAD_MARKER)
            return False
        if (os.path.exists(_FIRST_RUN_LOCK_FILE) and
                time.time() - os.path.getmtime(_FIRST_RUN_LOCK_FILE) < 7200):
            return False                      # never under first-run dialogs
        if xbmc.getCondVisibility('Player.HasMedia'):
            return False                      # don't disturb playback; retry later
        if xbmc.getCondVisibility('System.HasActiveModalDialog | '
                                  'Window.IsActive(busydialog) | '
                                  'Window.IsActive(busydialognocancel)'):
            return False
        # 3.2.47: never reload under a running script.skinvariables build -
        # its own ReloadSkin() comes at the end; ours would cut it short.
        from resources.lib import skin_rebuild
        home = xbmcgui.Window(10000)
        reason = skin_rebuild.busy()
        if reason:
            since = home.getProperty(_SV_DEFER_PROP)
            if not since:
                home.setProperty(_SV_DEFER_PROP, str(time.time()))
                _log('Skin reload waits for script.skinvariables (%s).' % reason)
                return False
            if time.time() - float(since) < _SV_MAX_DEFER:
                return False
            _log('script.skinvariables still busy after %ds (%s) - reloading anyway.'
                 % (_SV_MAX_DEFER, reason), xbmc.LOGWARNING)
        waited = home.getProperty(_SV_DEFER_PROP) and not reason
        home.clearProperty(_SV_DEFER_PROP)
        # skinvariables wrote its files AFTER our patch => it has just reloaded
        # the skin itself, patched files included. A second reload adds nothing.
        try:
            marked = os.path.getmtime(_SKIN_RELOAD_MARKER)
        except OSError:
            marked = 0
        if marked and skin_rebuild.last_generated_write() > marked:
            os.remove(_SKIN_RELOAD_MARKER)
            _log('script.skinvariables already reloaded the skin after the patch '
                 '- no extra reload.')
            return False
        os.remove(_SKIN_RELOAD_MARKER)
        if waited:
            _log('script.skinvariables finished - reloading skin now.')
        _log('Patched files in the active skin changed - reloading skin.')
        xbmc.executebuiltin('ReloadSkin()')
        return True
    except Exception as e:
        _log('Skin reload check failed: %s' % e, xbmc.LOGWARNING)
        return False


def _revert_search(wanted=None):
    from resources.lib import lucent_sources
    for profile in ('redlight_search', 'pov_search', 'umbrella_search'):
        aid = lucent_sources.SPECS[profile]['addon_id']
        if wanted is not None and aid not in wanted:
            continue
        addon_path = _resolve_addon_dir(aid)
        if addon_path:
            try:
                res = lucent_sources.revert(addon_path, profile)
            except Exception as e:
                res = (False, '[%s] Search All bridge revert failed: %s' % (aid, e))
            if res:
                yield res
    if wanted is None or 'plugin.video.themoviedb.helper' in wanted:
        player = os.path.join(xbmcvfs.translatePath('special://profile/addon_data/'),
                              'plugin.video.themoviedb.helper', AB_SEARCH_PLAYER)
        if os.path.isfile(player):
            try:
                os.remove(player)
                yield True, '[plugin.video.themoviedb.helper] Patched OK (reverted, toggle off): AB Search All player removed'
            except Exception as e:
                yield False, '[plugin.video.themoviedb.helper] could not remove %s: %s' % (AB_SEARCH_PLAYER, e)


def _revert_disabled(addon_ids=None):
    """Undo entries that carry 'revert_when_off' = (patched, stock) when their
    toggle is DISABLED. Plain one-shot string swap; yields (ok, msg)."""
    wanted = set(addon_ids) if addon_ids else None
    # Lucent theme (Toggles menu, per add-on): put the stock windows back and
    # remove the hooks for every add-on whose switch is off.
    from resources.lib import lucent_sources
    for aid, profile in lucent_sources.PROFILE_OF.items():
        if wanted is not None and aid not in wanted:
            continue
        if _feature_on('lucent_' + profile):
            continue
        addon_path = _resolve_addon_dir(aid)
        if not addon_path:
            continue
        try:
            res = lucent_sources.revert(addon_path, profile)
        except Exception as e:
            res = (False, '[%s] Glass theme revert failed: %s' % (aid, e))
        if res:
            yield res
    # Search All off: Red Light bridge out, TMDbHelper player file removed
    if not _feature_on('ab_search'):
        for res in _revert_search(wanted):
            yield res
    disabled = _load_disabled()
    if not disabled:
        return
    for patch in _all_patches():
        pair = patch.get('revert_when_off')
        if not pair or _toggle_of(patch) not in disabled:
            continue
        if wanted is not None and patch['addon_id'] not in wanted:
            continue
        addon_path = _resolve_addon_dir(patch['addon_id'])
        if patch.get('base') == 'addon_data':
            addon_path = os.path.join(ADDON_DATA, patch['addon_id'])
        if not addon_path:
            continue
        target = os.path.join(addon_path, patch['rel_path'])
        if not os.path.isfile(target):
            continue
        try:
            content = _read(target)
            if pair[0] not in content:
                continue
            _write(target, content.replace(pair[0], pair[1], 1))
            if patch.get('rescan_addons'):
                _RESCAN_PENDING[0] = True
            yield True, '[%s] Patched OK (reverted, toggle off): %s' % (
                patch['addon_id'], patch['description'])
        except Exception as e:
            yield False, '[%s] Revert failed: %s' % (patch['addon_id'], e)


_RESCAN_PENDING = [False]


def apply_set(group=None, addon_ids=None):
    """Silent patch core — no dialogs, safe to call from the service thread.

    Returns (succeeded, failed, changed, results) where `changed` counts only
    the entries that actually WROTE something this pass. Entries that were
    already patched are counted as succeeded but not as changed, so a caller
    can tell "nothing to do" from "an update wiped the patches and we just
    put them back".
    """
    _audit_sentinels()
    _log('Starting patch run … (group=%s, ids=%s)'
         % (group or 'default', ','.join(addon_ids) if addon_ids else 'all'))

    results   = []
    succeeded = 0
    failed    = 0
    changed   = 0

    # Reconcile the TinyPPI Arabic language folder to match the tinyppi_arabic
    # toggle STATE (handles both enable and disable; see _reconcile_tinyppi_arabic).
    # When TinyPPI is in scope, or the ACTIVE skin is (3.2.56): the PPI Arabic
    # fonts live in the active skin's Font.xml, which every skin update wipes.
    # A skin-only watchdog run used to leave them out, so the next full sweep
    # wrote them and reloaded the skin a second time.
    _scope = set(addon_ids or ())
    if (not addon_ids or 'script.tinyppi' in _scope
            or any(_is_active_skin(a) for a in _scope)):
        for ok, msg in _reconcile_tinyppi():
            _log(msg)
            results.append((ok, msg))
            if ok:
                succeeded += 1
                if ('Patched OK' in msg) or ('File injected OK' in msg):
                    changed += 1
            else:
                failed += 1

    for ok, msg in _revert_disabled(addon_ids):
        _log(msg)
        results.append((ok, msg))
        if ok:
            succeeded += 1
            changed += 1
        else:
            failed += 1

    for _n, patch in enumerate(_select(group, addon_ids), 1):
        # Numbered trace (DEBUG since 3.1.0.15) so Kodi's duplicate-message filter
        # (which swallows identical consecutive lines like the three dexworld
        # "Already patched" results) can't hide where a sweep stops.
        _trace('#%02d BEGIN %s -> %s' % (_n, patch['addon_id'], patch.get('rel_path')))
        ok, msg = _apply_patch(patch)
        if ok and patch.get('once') and 'Applied once already' not in msg \
                and 'not present' not in msg and 'not applicable' not in msg:
            from resources.lib import remote_patches
            remote_patches.mark_once(patch)
        _trace('#%02d END   %s' % (_n, msg))
        _log(msg)
        results.append((ok, msg))
        if ok:
            succeeded += 1
            # Count ONLY genuine writes. Every real write message carries
            # 'Patched OK' or 'File injected OK'; every no-op/skip does not
            # ('Already patched', 'Already present', 'Native support present
            # … skipping', optional 'not present – skipping'). The old
            # "'Already' not in msg" test mis-counted those skip messages as
            # writes, so a settled box reported "3 written" every sweep and the
            # watchdog popped a false 're-applied' toast.
            if ('Patched OK' in msg) or ('File injected OK' in msg):
                changed += 1
                if patch.get('rescan_addons'):
                    _RESCAN_PENDING[0] = True
                if _is_active_skin(patch['addon_id']):
                    _mark_skin_reload()
        else:
            failed += 1

    # 3.4.6: Font Size mode (original / +5% / -5%) - LAST, so font blocks the
    # patches above just added to the skin get scaled in the same pass. A skin
    # update brings stock sizes back; this puts the chosen mode back on.
    if not addon_ids or any(_is_active_skin(a) for a in _scope):
        try:
            from resources.lib import font_scale
            ok, msg, wrote = font_scale.reconcile()
        except Exception as e:
            ok, msg, wrote = False, '[font size] %s' % e, False
        _log(msg)
        results.append((ok, msg))
        if ok:
            succeeded += 1
        else:
            failed += 1
        if wrote:
            changed += 1
            _mark_skin_reload()

    # 3.4.26: an addon.xml changed ('rescan_addons') - Kodi only reads
    # addon.xml when it scans, so ask for a rescan now instead of a restart.
    if _RESCAN_PENDING[0]:
        _RESCAN_PENDING[0] = False
        _log('addon.xml changed - UpdateLocalAddons.')
        xbmc.executebuiltin('UpdateLocalAddons')

    _log('Patch run complete: %d OK, %d failed, %d written.'
         % (succeeded, failed, changed))
    return succeeded, failed, changed, results


def _choose_toggles():
    """Show the toggle checklist and persist the choice.

    Returns True to proceed with patching, False if the user cancelled. Only
    toggles whose add-on is installed are shown, so the list never offers a
    group that can't do anything. The checklist is pre-ticked from the saved
    state (a toggle with no saved state defaults to ON).
    """
    disabled = _load_disabled()

    # Which add-ons are actually present, so we only show usable toggles.
    all_patches = _all_patches()
    present = set()
    for patch in all_patches:
        if _resolve_addon_dir(patch['addon_id']):
            present.add(patch['addon_id'])

    toggle_has_installed = set()
    for patch in all_patches:
        tid = _toggle_of(patch)
        if tid and patch['addon_id'] in present:
            toggle_has_installed.add(tid)

    shown = [(tid, label) for tid, label in _toggle_groups()
             if tid in toggle_has_installed]

    # No installed add-on maps to any toggle: nothing to choose, just proceed
    # (the always-on fixes and any present grouped patches still apply).
    if not shown:
        return True

    # 3.2.23: a list of on/off switches (toggle art) instead of checkboxes;
    # picking a row flips it, "Done - apply" runs the patches.
    from resources.lib import toggle_ui
    from resources.lib.i18n import T
    states = toggle_ui.switch_list(
        '%s – choose what to patch' % ADDON_NAME,
        [(tid, label, tid not in disabled) for tid, label in shown],
        confirm_back=(T(30750), T(30751), T(30752)))

    # Back (or "Discard") -> abort the whole run, leave saved toggles untouched.
    if states is None:
        _log('Toggle checklist closed without saving - nothing changed.')
        return None

    # Toggles not shown (add-on absent) keep their previous state so a temporary
    # uninstall doesn't silently flip them.
    new_disabled = set(disabled)
    for tid, on in states.items():
        if on:
            new_disabled.discard(tid)
        else:
            new_disabled.add(tid)
    flipped = new_disabled ^ disabled
    if _save_disabled(new_disabled):
        _log('Toggles saved: off=%s%s' % (
            ','.join(sorted(new_disabled)) or 'none',
            ' (changed: %s)' % ','.join(sorted(flipped)) if flipped else ''))
    return flipped


def run(group=None, addon_ids=None):
    """Entry point called from default.py router ("Apply Patches").

    The toggle checklist is a MANDATORY pre-step: it always runs first, and the
    user's choice decides which grouped patches get applied. Always-on stability
    fixes apply regardless. Cancelling the checklist aborts the run entirely.

    addon_ids=[...] still narrows to specific add-ons (used by callers that want
    a one-off re-apply); the toggle filter in _select() applies on top of it.
    """
    if _choose_toggles() is None:
        return  # user cancelled the checklist

    succeeded, failed, _changed, results = apply_set(group, addon_ids=addon_ids)

    lines = []
    for ok, msg in results:
        icon    = '[COLOR lime]\u2714[/COLOR]' if ok else '[COLOR red]\u2718[/COLOR]'
        display = re.sub(r'^\[.*?\]\s*', '', msg)
        lines.append('%s  %s' % (icon, display))

    disabled = _load_disabled()
    summary = '[B]Patch Results[/B][CR][CR]' + '[CR]'.join(lines)
    summary += '[CR][CR]%d succeeded,  %d failed.' % (succeeded, failed)
    if disabled:
        labels = dict(_toggle_groups())
        off = ', '.join(labels.get(t, t) for t in sorted(disabled))
        summary += '[CR]Disabled: %s' % off

    DIALOG.ok(ADDON_NAME, summary)
    reload_skin_if_pending()

