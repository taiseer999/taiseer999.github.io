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
        'already_patched_check': '# -- TMDbHelper Trakt QR Auth patch (by ABUKARIM TOOLS) --',
        # Version-resilient fallback: replace the whole poller() method by anchor,
        # regardless of minor whitespace/line drift between TMDbHelper releases.
        'fallback_pattern': r'    def poller\(self\):\n[\s\S]*?\n(?=    mutex_lockname)',
        'fallback_repl': (lambda _b: (lambda m: base64.b64decode(_b).decode('utf-8') + '\n'))(_TMDBH_POLLER_NEW_B64),
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
        'already_patched_check': '# -- USA certification fallback (by ABUKARIM TOOLS) --',
        'fallback_pattern': r"conditions = 'parent_id=\? AND iso_country=\? AND name IS NOT NULL",
        'fallback_repl': (
            'conditions = \'parent_id=? AND iso_country IN (?, \"US\") AND name IS NOT NULL'
        ),
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
    ('tinyppi_codecs',   'TinyPPI: Codec Badges'),
    ('tinyppi_audio',    'TinyPPI: Audio Badges'),
    ('tinyppi_arabic',   'PPI Arabic'),
    ('ppi_af3',          'PPI AF3 Dialog (native)'),
    ('af3_vplot',        'AF3: Vertical Plot (Home, OSD & Views)'),
    ('af3_highlight',    'AF3: Highlight Genre & Widget Titles'),
    ('redlight_fixes',   'RedLight: Fix Sound & Theme'),
    ('fenlight_volume',  'Fenlight: Kill Volume Auto-Drop'),
    ('a4ksubs_utf8',     'a4kSubtitles: UTF-8 Subtitles Fix'),
    ('a4ksubs_quiet',    'a4kSubtitles: Hide Account/API-Key Nags'),
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
    if name == 'af3_trailers':
        try:
            from resources.lib.af3_trailers import config as _trailers_config
            return _trailers_config.load().get('enabled', False)
        except Exception:
            return False
    return False


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
        os.remove(_SKIN_RELOAD_MARKER)
        _log('Patched files in the active skin changed - reloading skin.')
        xbmc.executebuiltin('ReloadSkin()')
        return True
    except Exception as e:
        _log('Skin reload check failed: %s' % e, xbmc.LOGWARNING)
        return False


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
    # Only when TinyPPI is in scope for this run.
    if not addon_ids or 'script.tinyppi' in set(addon_ids):
        for ok, msg in _reconcile_tinyppi():
            _log(msg)
            results.append((ok, msg))
            if ok:
                succeeded += 1
                if ('Patched OK' in msg) or ('File injected OK' in msg):
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
                if _is_active_skin(patch['addon_id']):
                    _mark_skin_reload()
        else:
            failed += 1

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
    states = toggle_ui.switch_list(
        '%s – choose what to patch' % ADDON_NAME,
        [(tid, label, tid not in disabled) for tid, label in shown])

    # Back -> abort the whole run, leave saved toggles untouched.
    if states is None:
        return False

    # Toggles not shown (add-on absent) keep their previous state so a temporary
    # uninstall doesn't silently flip them.
    new_disabled = set(disabled)
    for tid, on in states.items():
        if on:
            new_disabled.discard(tid)
        else:
            new_disabled.add(tid)
    _save_disabled(new_disabled)
    return True


def run(group=None, addon_ids=None):
    """Entry point called from default.py router ("Apply Patches").

    The toggle checklist is a MANDATORY pre-step: it always runs first, and the
    user's choice decides which grouped patches get applied. Always-on stability
    fixes apply regardless. Cancelling the checklist aborts the run entirely.

    addon_ids=[...] still narrows to specific add-ons (used by callers that want
    a one-off re-apply); the toggle filter in _select() applies on top of it.
    """
    if not _choose_toggles():
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
