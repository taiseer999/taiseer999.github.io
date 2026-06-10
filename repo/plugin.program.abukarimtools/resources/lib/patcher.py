# -*- coding: utf-8 -*-
"""
patcher.py  –  ABUKARIM TOOLS
Applies patches to installed Kodi addons:

  1. plugin.video.redlight  –  kodi_utils.py
     addon_themes() → Dark only (removes Light & Medium options)

  2. script.tinyppi  –  overlay.py
     _ALLOW_NON_COREELEC = False  →  True

  3. script.tinyppi  –  resources/lib/properties.py
     get_DoviProfileVar() → strip "Dolby Vision " prefix, return profile part only

  4. script.tinyppi  –  resources/lib/monitor.py
     onNotification() → add _update_hdr_properties() trigger on Player.OnPlay

  5. script.tinyppi  –  resources/lib/monitor.py
     Add _update_hdr_properties() method to KodiMonitor class
"""

import base64
import os
import re
import xbmc
import xbmcvfs
import xbmcgui

_SEREN_QR_UTILS_B64 = 'IyAtKi0gY29kaW5nOiB1dGYtOCAtKi0KIiIiClFSIENvZGUgdXRpbGl0aWVzIGZvciBTZXJlbgrZitmD2KrYqCDYp9mE2LXZiNix2Kkg2LnYqNixIHhibWN2ZnMg2YjZitix2KzYuSBzcGVjaWFsOi8vIHBhdGgKIiIiCmltcG9ydCBvcwppbXBvcnQgc3lzCmltcG9ydCB4Ym1jCmltcG9ydCB4Ym1jYWRkb24KaW1wb3J0IHhibWN2ZnMKCgpkZWYgX2luamVjdF9xcl9wYXRocygpOgogICAgdHJ5OgogICAgICAgIG91cl9wYXRoICAgID0geGJtY2FkZG9uLkFkZG9uKCdwbHVnaW4udmlkZW8uc2VyZW4nKS5nZXRBZGRvbkluZm8oJ3BhdGgnKQogICAgICAgIGFkZG9uc19yb290ID0gb3MucGF0aC5kaXJuYW1lKG91cl9wYXRoKQogICAgICAgIGZvciBtb2R1bGUgaW4gKCdzY3JpcHQubW9kdWxlLnFyY29kZScsICdzY3JpcHQubW9kdWxlLnBpbCcpOgogICAgICAgICAgICBsaWJfcGF0aCA9IG9zLnBhdGguam9pbihhZGRvbnNfcm9vdCwgbW9kdWxlLCAnbGliJykKICAgICAgICAgICAgaWYgb3MucGF0aC5pc2RpcihsaWJfcGF0aCkgYW5kIGxpYl9wYXRoIG5vdCBpbiBzeXMucGF0aDoKICAgICAgICAgICAgICAgIHN5cy5wYXRoLmluc2VydCgwLCBsaWJfcGF0aCkKICAgIGV4Y2VwdCBFeGNlcHRpb246CiAgICAgICAgcGFzcwoKCmRlZiBfZ2V0X3FyX3NwZWNpYWxfcGF0aCgpOgogICAgIiIi2YXYs9in2LEg2KvYp9io2Kog2YHZiiBhZGRvbl9kYXRhINmK2LbZhdmGINmI2LXZiNmEIEtvZGkg2KXZhNmK2YciIiIKICAgIHJldHVybiAnc3BlY2lhbDovL3Byb2ZpbGUvYWRkb25fZGF0YS9wbHVnaW4udmlkZW8uc2VyZW4vc2VyZW5fcXIucG5nJwoKCmRlZiBfbWFrZV9xcl9sb2NhbCh1cmwsIG9zX3BhdGgpOgogICAgaW1wb3J0IHFyY29kZQogICAgaW1nID0gcXJjb2RlLm1ha2UodXJsKQogICAgaW1nLnNhdmUob3NfcGF0aCkKICAgIHJldHVybiBUcnVlCgoKZGVmIF9tYWtlX3FyX3JlbW90ZSh1cmwsIG9zX3BhdGgpOgogICAgZnJvbSB1cmxsaWIucmVxdWVzdCBpbXBvcnQgdXJsb3BlbgogICAgZnJvbSB1cmxsaWIucGFyc2UgICBpbXBvcnQgcXVvdGUKICAgIGFwaV91cmwgPSAnaHR0cHM6Ly9hcGkucXJzZXJ2ZXIuY29tL3YxL2NyZWF0ZS1xci1jb2RlLz9zaXplPTQwMHg0MDAmZGF0YT0nICsgcXVvdGUodXJsLCBzYWZlPScnKQogICAgd2l0aCB1cmxvcGVuKGFwaV91cmwsIHRpbWVvdXQ9MTApIGFzIHJlc3A6CiAgICAgICAgZGF0YSA9IHJlc3AucmVhZCgpCiAgICBpZiBsZW4oZGF0YSkgPCAxMDA6CiAgICAgICAgcmFpc2UgVmFsdWVFcnJvcignRW1wdHkgUVIgcmVzcG9uc2UnKQogICAgd2l0aCBvcGVuKG9zX3BhdGgsICd3YicpIGFzIGY6CiAgICAgICAgZi53cml0ZShkYXRhKQogICAgcmV0dXJuIFRydWUKCgpkZWYgbWFrZV9xcih1cmwpOgogICAgIiIiCiAgICDZitmI2YTZkdivIFFSIFBORyDZgdmKIGFkZG9uX2RhdGEg2YjZitix2KzYuSBzcGVjaWFsOi8vIHBhdGgKICAgIGFkZG9uX2RhdGEg2YXYttmF2YjZhiDYo9mGIEtvZGkg2YrYrdmF2ZHZhCDZhdmG2Ycg2KfZhNi12YjYsSDZhdio2KfYtNix2KkKICAgICIiIgogICAgX2luamVjdF9xcl9wYXRocygpCgogICAgc3BlY2lhbF9wYXRoID0gX2dldF9xcl9zcGVjaWFsX3BhdGgoKQogICAgb3NfcGF0aCAgICAgID0geGJtY3Zmcy50cmFuc2xhdGVQYXRoKHNwZWNpYWxfcGF0aCkKCiAgICAjINmG2KrYo9mD2K8g2YXZhiDZiNis2YjYryDYp9mE2YXYrNmE2K8KICAgIG9zLm1ha2VkaXJzKG9zLnBhdGguZGlybmFtZShvc19wYXRoKSwgZXhpc3Rfb2s9VHJ1ZSkKCiAgICAjINmF2K3Yp9mI2YTYqSAxOiDZhdit2YTZigogICAgdHJ5OgogICAgICAgIF9tYWtlX3FyX2xvY2FsKHVybCwgb3NfcGF0aCkKICAgICAgICB4Ym1jLmxvZyhmJ1NlcmVuIFFSIGxvY2FsIE9LOiB7c3BlY2lhbF9wYXRofScsIHhibWMuTE9HSU5GTykKICAgICAgICByZXR1cm4gc3BlY2lhbF9wYXRoCiAgICBleGNlcHQgRXhjZXB0aW9uIGFzIGU6CiAgICAgICAgeGJtYy5sb2coZidTZXJlbiBRUiBsb2NhbCBmYWlsZWQ6IHtlfSDigJQgdHJ5aW5nIHJlbW90ZScsIHhibWMuTE9HSU5GTykKCiAgICAjINmF2K3Yp9mI2YTYqSAyOiBBUEkKICAgIHRyeToKICAgICAgICBfbWFrZV9xcl9yZW1vdGUodXJsLCBvc19wYXRoKQogICAgICAgIHhibWMubG9nKGYnU2VyZW4gUVIgcmVtb3RlIE9LOiB7c3BlY2lhbF9wYXRofScsIHhibWMuTE9HSU5GTykKICAgICAgICByZXR1cm4gc3BlY2lhbF9wYXRoCiAgICBleGNlcHQgRXhjZXB0aW9uIGFzIGU6CiAgICAgICAgeGJtYy5sb2coZidTZXJlbiBRUiByZW1vdGUgZmFpbGVkOiB7ZX0nLCB4Ym1jLkxPR1dBUk5JTkcpCgogICAgcmV0dXJuICcnCgoKZGVmIHJlbW92ZV9xcihwYXRoKToKICAgIHRyeToKICAgICAgICBpZiBwYXRoOgogICAgICAgICAgICBvc19wYXRoID0geGJtY3Zmcy50cmFuc2xhdGVQYXRoKHBhdGgpIGlmIHBhdGguc3RhcnRzd2l0aCgnc3BlY2lhbDovLycpIGVsc2UgcGF0aAogICAgICAgICAgICBpZiBvcy5wYXRoLmV4aXN0cyhvc19wYXRoKToKICAgICAgICAgICAgICAgIG9zLnJlbW92ZShvc19wYXRoKQogICAgZXhjZXB0IEV4Y2VwdGlvbjoKICAgICAgICBwYXNzCg=='
_SEREN_XML_B64 = 'PHdpbmRvdyB0eXBlPSJkaWFsb2ciPgogICAgPGNvb3JkaW5hdGVzPgogICAgICAgIDxsZWZ0PjA8L2xlZnQ+CiAgICAgICAgPHRvcD4wPC90b3A+CiAgICAgICAgPHdpZHRoPjE5MjA8L3dpZHRoPgogICAgICAgIDxoZWlnaHQ+MTA4MDwvaGVpZ2h0PgogICAgPC9jb29yZGluYXRlcz4KICAgIDxjb250cm9scz4KCiAgICAgICAgPCEtLSBEaW0gb3ZlcmxheSAtLT4KICAgICAgICA8Y29udHJvbCB0eXBlPSJpbWFnZSI+CiAgICAgICAgICAgIDxsZWZ0PjA8L2xlZnQ+PHRvcD4wPC90b3A+CiAgICAgICAgICAgIDx3aWR0aD4xOTIwPC93aWR0aD48aGVpZ2h0PjEwODA8L2hlaWdodD4KICAgICAgICAgICAgPHRleHR1cmUgYmFja2dyb3VuZD0idHJ1ZSI+d2hpdGUucG5nPC90ZXh0dXJlPgogICAgICAgICAgICA8Y29sb3JkaWZmdXNlPkQwMDAwMDAwPC9jb2xvcmRpZmZ1c2U+CiAgICAgICAgPC9jb250cm9sPgoKICAgICAgICA8IS0tIENhcmQgYmFja2dyb3VuZCAtLT4KICAgICAgICA8Y29udHJvbCB0eXBlPSJpbWFnZSI+CiAgICAgICAgICAgIDxsZWZ0PjQxMDwvbGVmdD48dG9wPjE2NTwvdG9wPgogICAgICAgICAgICA8d2lkdGg+MTEwMDwvd2lkdGg+PGhlaWdodD43NTA8L2hlaWdodD4KICAgICAgICAgICAgPHRleHR1cmUgYmFja2dyb3VuZD0idHJ1ZSI+d2hpdGUucG5nPC90ZXh0dXJlPgogICAgICAgICAgICA8Y29sb3JkaWZmdXNlPkZGMUExQTFBPC9jb2xvcmRpZmZ1c2U+CiAgICAgICAgPC9jb250cm9sPgoKICAgICAgICA8IS0tIFJlZCB0b3AgYmFyIC0tPgogICAgICAgIDxjb250cm9sIHR5cGU9ImltYWdlIj4KICAgICAgICAgICAgPGxlZnQ+NDEwPC9sZWZ0Pjx0b3A+MTY1PC90b3A+CiAgICAgICAgICAgIDx3aWR0aD4xMTAwPC93aWR0aD48aGVpZ2h0Pjg8L2hlaWdodD4KICAgICAgICAgICAgPHRleHR1cmUgYmFja2dyb3VuZD0idHJ1ZSI+d2hpdGUucG5nPC90ZXh0dXJlPgogICAgICAgICAgICA8Y29sb3JkaWZmdXNlPkZGRUQxQzI0PC9jb2xvcmRpZmZ1c2U+CiAgICAgICAgPC9jb250cm9sPgoKICAgICAgICA8IS0tIFRpdGxlIC0tPgogICAgICAgIDxjb250cm9sIHR5cGU9ImxhYmVsIj4KICAgICAgICAgICAgPGxlZnQ+NDEwPC9sZWZ0Pjx0b3A+MTk1PC90b3A+CiAgICAgICAgICAgIDx3aWR0aD4xMTAwPC93aWR0aD48aGVpZ2h0PjYwPC9oZWlnaHQ+CiAgICAgICAgICAgIDxhbGlnbj5jZW50ZXI8L2FsaWduPgogICAgICAgICAgICA8Zm9udD5mb250Mjc8L2ZvbnQ+CiAgICAgICAgICAgIDx0ZXh0Y29sb3I+RkZFRDFDMjQ8L3RleHRjb2xvcj4KICAgICAgICAgICAgPGxhYmVsPlRyYWt0IEF1dGhvcml6YXRpb248L2xhYmVsPgogICAgICAgIDwvY29udHJvbD4KCiAgICAgICAgPCEtLSBRUiB3aGl0ZSBiYWNrZ3JvdW5kIC0tPgogICAgICAgIDxjb250cm9sIHR5cGU9ImltYWdlIj4KICAgICAgICAgICAgPGxlZnQ+NDU1PC9sZWZ0Pjx0b3A+Mjc1PC90b3A+CiAgICAgICAgICAgIDx3aWR0aD40MjA8L3dpZHRoPjxoZWlnaHQ+NDIwPC9oZWlnaHQ+CiAgICAgICAgICAgIDx0ZXh0dXJlIGJhY2tncm91bmQ9InRydWUiPndoaXRlLnBuZzwvdGV4dHVyZT4KICAgICAgICAgICAgPGNvbG9yZGlmZnVzZT5GRkZGRkZGRjwvY29sb3JkaWZmdXNlPgogICAgICAgIDwvY29udHJvbD4KCiAgICAgICAgPCEtLSBRUiBDb2RlIC0tPgogICAgICAgIDxjb250cm9sIHR5cGU9ImltYWdlIj4KICAgICAgICAgICAgPGxlZnQ+NDY1PC9sZWZ0Pjx0b3A+Mjg1PC90b3A+CiAgICAgICAgICAgIDx3aWR0aD40MDA8L3dpZHRoPjxoZWlnaHQ+NDAwPC9oZWlnaHQ+CiAgICAgICAgICAgIDxhc3BlY3RyYXRpbz5zdHJldGNoPC9hc3BlY3RyYXRpbz4KICAgICAgICAgICAgPHRleHR1cmU+JElORk9bV2luZG93KCkuUHJvcGVydHkocXJfaW1hZ2UpXTwvdGV4dHVyZT4KICAgICAgICA8L2NvbnRyb2w+CgogICAgICAgIDwhLS0gU2NhbiBpbnN0cnVjdGlvbiAtLT4KICAgICAgICA8Y29udHJvbCB0eXBlPSJsYWJlbCI+CiAgICAgICAgICAgIDxsZWZ0PjkzMDwvbGVmdD48dG9wPjI5NTwvdG9wPgogICAgICAgICAgICA8d2lkdGg+NTMwPC93aWR0aD48aGVpZ2h0PjQwPC9oZWlnaHQ+CiAgICAgICAgICAgIDxmb250PmZvbnQxMjwvZm9udD4KICAgICAgICAgICAgPHRleHRjb2xvcj5GRkFBQUFBQTwvdGV4dGNvbG9yPgogICAgICAgICAgICA8bGFiZWw+U2NhbiBRUiBjb2RlIG9yIHZpc2l0OjwvbGFiZWw+CiAgICAgICAgPC9jb250cm9sPgoKICAgICAgICA8IS0tIFVSTCAtLT4KICAgICAgICA8Y29udHJvbCB0eXBlPSJsYWJlbCI+CiAgICAgICAgICAgIDxsZWZ0PjkzMDwvbGVmdD48dG9wPjM1MDwvdG9wPgogICAgICAgICAgICA8d2lkdGg+NTMwPC93aWR0aD48aGVpZ2h0PjQwPC9oZWlnaHQ+CiAgICAgICAgICAgIDxmb250PmZvbnQxMjwvZm9udD4KICAgICAgICAgICAgPHRleHRjb2xvcj5GRkVEMUMyNDwvdGV4dGNvbG9yPgogICAgICAgICAgICA8bGFiZWw+aHR0cHM6Ly90cmFrdC50di9hY3RpdmF0ZTwvbGFiZWw+CiAgICAgICAgPC9jb250cm9sPgoKICAgICAgICA8IS0tIERpdmlkZXIgLS0+CiAgICAgICAgPGNvbnRyb2wgdHlwZT0iaW1hZ2UiPgogICAgICAgICAgICA8bGVmdD45MzA8L2xlZnQ+PHRvcD40MTA8L3RvcD4KICAgICAgICAgICAgPHdpZHRoPjUzMDwvd2lkdGg+PGhlaWdodD4yPC9oZWlnaHQ+CiAgICAgICAgICAgIDx0ZXh0dXJlIGJhY2tncm91bmQ9InRydWUiPndoaXRlLnBuZzwvdGV4dHVyZT4KICAgICAgICAgICAgPGNvbG9yZGlmZnVzZT40NEZGRkZGRjwvY29sb3JkaWZmdXNlPgogICAgICAgIDwvY29udHJvbD4KCiAgICAgICAgPCEtLSBFbnRlciBDb2RlIGxhYmVsIC0tPgogICAgICAgIDxjb250cm9sIHR5cGU9ImxhYmVsIj4KICAgICAgICAgICAgPGxlZnQ+OTMwPC9sZWZ0Pjx0b3A+NDMwPC90b3A+CiAgICAgICAgICAgIDx3aWR0aD41MzA8L3dpZHRoPjxoZWlnaHQ+NDA8L2hlaWdodD4KICAgICAgICAgICAgPGZvbnQ+Zm9udDEyPC9mb250PgogICAgICAgICAgICA8dGV4dGNvbG9yPkZGQUFBQUFBPC90ZXh0Y29sb3I+CiAgICAgICAgICAgIDxsYWJlbD5FbnRlciB0aGlzIGNvZGU6PC9sYWJlbD4KICAgICAgICA8L2NvbnRyb2w+CgogICAgICAgIDwhLS0gQ29kZSBib3ggYm9yZGVyIC0tPgogICAgICAgIDxjb250cm9sIHR5cGU9ImltYWdlIj4KICAgICAgICAgICAgPGxlZnQ+OTMwPC9sZWZ0Pjx0b3A+NDgwPC90b3A+CiAgICAgICAgICAgIDx3aWR0aD41MzA8L3dpZHRoPjxoZWlnaHQ+ODA8L2hlaWdodD4KICAgICAgICAgICAgPHRleHR1cmUgYmFja2dyb3VuZD0idHJ1ZSI+d2hpdGUucG5nPC90ZXh0dXJlPgogICAgICAgICAgICA8Y29sb3JkaWZmdXNlPkZGRUQxQzI0PC9jb2xvcmRpZmZ1c2U+CiAgICAgICAgPC9jb250cm9sPgoKICAgICAgICA8IS0tIENvZGUgYm94IGZpbGwgLS0+CiAgICAgICAgPGNvbnRyb2wgdHlwZT0iaW1hZ2UiPgogICAgICAgICAgICA8bGVmdD45MzQ8L2xlZnQ+PHRvcD40ODQ8L3RvcD4KICAgICAgICAgICAgPHdpZHRoPjUyMjwvd2lkdGg+PGhlaWdodD43MjwvaGVpZ2h0PgogICAgICAgICAgICA8dGV4dHVyZSBiYWNrZ3JvdW5kPSJ0cnVlIj53aGl0ZS5wbmc8L3RleHR1cmU+CiAgICAgICAgICAgIDxjb2xvcmRpZmZ1c2U+RkYxQTFBMUE8L2NvbG9yZGlmZnVzZT4KICAgICAgICA8L2NvbnRyb2w+CgogICAgICAgIDwhLS0gVXNlciBDb2RlIC0tPgogICAgICAgIDxjb250cm9sIHR5cGU9ImxhYmVsIj4KICAgICAgICAgICAgPGxlZnQ+OTMwPC9sZWZ0Pjx0b3A+NDg0PC90b3A+CiAgICAgICAgICAgIDx3aWR0aD41MzA8L3dpZHRoPjxoZWlnaHQ+NzI8L2hlaWdodD4KICAgICAgICAgICAgPGFsaWduPmNlbnRlcjwvYWxpZ24+CiAgICAgICAgICAgIDxhbGlnbnk+Y2VudGVyPC9hbGlnbnk+CiAgICAgICAgICAgIDxmb250PmZvbnQzNzwvZm9udD4KICAgICAgICAgICAgPHRleHRjb2xvcj5GRkVEMUMyNDwvdGV4dGNvbG9yPgogICAgICAgICAgICA8bGFiZWw+JElORk9bV2luZG93KCkuUHJvcGVydHkodXNlcl9jb2RlKV08L2xhYmVsPgogICAgICAgIDwvY29udHJvbD4KCiAgICAgICAgPCEtLSBQcm9ncmVzcyBiYXIgYmFja2dyb3VuZCAtLT4KICAgICAgICA8Y29udHJvbCB0eXBlPSJpbWFnZSI+CiAgICAgICAgICAgIDxsZWZ0PjkzMDwvbGVmdD48dG9wPjU5MDwvdG9wPgogICAgICAgICAgICA8d2lkdGg+NTMwPC93aWR0aD48aGVpZ2h0Pjg8L2hlaWdodD4KICAgICAgICAgICAgPHRleHR1cmUgYmFja2dyb3VuZD0idHJ1ZSI+d2hpdGUucG5nPC90ZXh0dXJlPgogICAgICAgICAgICA8Y29sb3JkaWZmdXNlPjQ0RkZGRkZGPC9jb2xvcmRpZmZ1c2U+CiAgICAgICAgPC9jb250cm9sPgoKICAgICAgICA8IS0tIFByb2dyZXNzIGJhciBmaWxsIC0tPgogICAgICAgIDxjb250cm9sIHR5cGU9ImltYWdlIj4KICAgICAgICAgICAgPGxlZnQ+OTMwPC9sZWZ0Pjx0b3A+NTkwPC90b3A+CiAgICAgICAgICAgIDx3aWR0aD4kSU5GT1tXaW5kb3coKS5Qcm9wZXJ0eShwcm9ncmVzc193aWR0aCldPC93aWR0aD48aGVpZ2h0Pjg8L2hlaWdodD4KICAgICAgICAgICAgPHRleHR1cmUgYmFja2dyb3VuZD0idHJ1ZSI+d2hpdGUucG5nPC90ZXh0dXJlPgogICAgICAgICAgICA8Y29sb3JkaWZmdXNlPkZGRUQxQzI0PC9jb2xvcmRpZmZ1c2U+CiAgICAgICAgPC9jb250cm9sPgoKICAgICAgICA8IS0tIEV4cGlyZXMgbGFiZWwgLS0+CiAgICAgICAgPGNvbnRyb2wgdHlwZT0ibGFiZWwiPgogICAgICAgICAgICA8bGVmdD45MzA8L2xlZnQ+PHRvcD42MTA8L3RvcD4KICAgICAgICAgICAgPHdpZHRoPjUzMDwvd2lkdGg+PGhlaWdodD4zNTwvaGVpZ2h0PgogICAgICAgICAgICA8Zm9udD5mb250X3Rpbnk8L2ZvbnQ+CiAgICAgICAgICAgIDx0ZXh0Y29sb3I+RkY4ODg4ODg8L3RleHRjb2xvcj4KICAgICAgICAgICAgPGxhYmVsPiRJTkZPW1dpbmRvdygpLlByb3BlcnR5KGV4cGlyZXNfbGFiZWwpXTwvbGFiZWw+CiAgICAgICAgPC9jb250cm9sPgoKICAgICAgICA8IS0tIENhbmNlbCBoaW50IC0tPgogICAgICAgIDxjb250cm9sIHR5cGU9ImxhYmVsIj4KICAgICAgICAgICAgPGxlZnQ+NDEwPC9sZWZ0Pjx0b3A+ODcwPC90b3A+CiAgICAgICAgICAgIDx3aWR0aD4xMTAwPC93aWR0aD48aGVpZ2h0PjM1PC9oZWlnaHQ+CiAgICAgICAgICAgIDxhbGlnbj5jZW50ZXI8L2FsaWduPgogICAgICAgICAgICA8Zm9udD5mb250X3Rpbnk8L2ZvbnQ+CiAgICAgICAgICAgIDx0ZXh0Y29sb3I+RkY2NjY2NjY8L3RleHRjb2xvcj4KICAgICAgICAgICAgPGxhYmVsPlByZXNzIEJhY2sgdG8gY2FuY2VsPC9sYWJlbD4KICAgICAgICA8L2NvbnRyb2w+CgogICAgPC9jb250cm9scz4KPC93aW5kb3c+Cg=='
_SEREN_OLD_B64 = 'ICAgICAgICB0b29scy5jb3B5MmNsaXAodXNlcl9jb2RlKQ0KICAgICAgICBmYWlsZWQgPSBGYWxzZQ0KICAgICAgICB0cnk6DQogICAgICAgICAgICBwcm9ncmVzc19kaWFsb2cgPSB4Ym1jZ3VpLkRpYWxvZ1Byb2dyZXNzKCkNCiAgICAgICAgICAgIHByb2dyZXNzX2RpYWxvZy5jcmVhdGUoDQogICAgICAgICAgICAgICAgZiJ7Zy5BRERPTl9OQU1FfToge2cuZ2V0X2xhbmd1YWdlX3N0cmluZygzMDAyMil9IiwNCiAgICAgICAgICAgICAgICB0b29scy5jcmVhdGVfbXVsdGlsaW5lX21lc3NhZ2UoDQogICAgICAgICAgICAgICAgICAgIGxpbmUxPWcuZ2V0X2xhbmd1YWdlX3N0cmluZygzMDAxOCkuZm9ybWF0KGcuY29sb3Jfc3RyaW5nKCJodHRwczovL3RyYWt0LnR2L2FjdGl2YXRlIikpLA0KICAgICAgICAgICAgICAgICAgICBsaW5lMj1nLmdldF9sYW5ndWFnZV9zdHJpbmcoMzAwMTkpLmZvcm1hdChnLmNvbG9yX3N0cmluZyh1c2VyX2NvZGUpKSwNCiAgICAgICAgICAgICAgICAgICAgbGluZTM9Zy5nZXRfbGFuZ3VhZ2Vfc3RyaW5nKDMwMDQ3KSwNCiAgICAgICAgICAgICAgICApLA0KICAgICAgICAgICAgKQ0KICAgICAgICAgICAgcHJvZ3Jlc3NfZGlhbG9nLnVwZGF0ZSgxMDApDQogICAgICAgICAgICB3aGlsZSBub3QgZmFpbGVkIGFuZCBzZWxmLnVzZXJuYW1lIGlzIE5vbmUgYW5kIHRva2VuX3R0bCA+IDAgYW5kIG5vdCBwcm9ncmVzc19kaWFsb2cuaXNjYW5jZWxlZCgpOg0KICAgICAgICAgICAgICAgIHhibWMuc2xlZXAoMTAwMCkNCiAgICAgICAgICAgICAgICBpZiB0b2tlbl90dGwgJSBpbnRlcnZhbCA9PSAwOg0KICAgICAgICAgICAgICAgICAgICBmYWlsZWQgPSBzZWxmLl9hdXRoX3BvbGwoZGV2aWNlKQ0KICAgICAgICAgICAgICAgIHByb2dyZXNzX3BlcmNlbnQgPSBpbnQoZmxvYXQoKHRva2VuX3R0bCAqIDEwMCkgLyBleHBpcnkpKQ0KICAgICAgICAgICAgICAgIHByb2dyZXNzX2RpYWxvZy51cGRhdGUocHJvZ3Jlc3NfcGVyY2VudCkNCiAgICAgICAgICAgICAgICB0b2tlbl90dGwgLT0gMQ0KDQogICAgICAgICAgICBwcm9ncmVzc19kaWFsb2cuY2xvc2UoKQ0KICAgICAgICBmaW5hbGx5Og0KICAgICAgICAgICAgZGVsIHByb2dyZXNzX2RpYWxvZw0KDQo='
_SEREN_NEW_B64 = 'ICAgICAgICB0b29scy5jb3B5MmNsaXAodXNlcl9jb2RlKQ0KDQogICAgICAgICMgLS0gU2VyZW4gUVIgQXV0aCBwYXRjaCAoYnkgQUJVS0FSSU0gVE9PTFMpIC0tDQogICAgICAgIGZyb20gcmVzb3VyY2VzLmxpYi5xcl91dGlscyBpbXBvcnQgbWFrZV9xciwgcmVtb3ZlX3FyDQogICAgICAgIHFyX3VybCAgICA9ICJodHRwczovL3RyYWt0LnR2L2FjdGl2YXRlLyIgKyB1c2VyX2NvZGUNCiAgICAgICAgcXJfcGF0aCAgID0gbWFrZV9xcihxcl91cmwpDQogICAgICAgIGFkZG9uX3BhdGggPSBnLkFERE9OLmdldEFkZG9uSW5mbygicGF0aCIpDQogICAgICAgIHFyX2RpYWxvZyA9IHhibWNndWkuV2luZG93WE1MRGlhbG9nKCJ0cmFrdF9hdXRoX3FyLnhtbCIsIGFkZG9uX3BhdGgsICJEZWZhdWx0IikNCiAgICAgICAgcXJfZGlhbG9nLnNldFByb3BlcnR5KCJ1c2VyX2NvZGUiLCAgICAgIHVzZXJfY29kZSkNCiAgICAgICAgcXJfZGlhbG9nLnNldFByb3BlcnR5KCJxcl9pbWFnZSIsICAgICAgIHFyX3BhdGgpDQogICAgICAgIHFyX2RpYWxvZy5zZXRQcm9wZXJ0eSgicHJvZ3Jlc3Nfd2lkdGgiLCAiNTMwIikNCiAgICAgICAgcXJfZGlhbG9nLnNldFByb3BlcnR5KCJleHBpcmVzX2xhYmVsIiwgIGYiRXhwaXJlcyBpbiB7dG9rZW5fdHRsfXMiKQ0KICAgICAgICBxcl9kaWFsb2cuc2hvdygpDQogICAgICAgIGZhaWxlZCA9IEZhbHNlDQogICAgICAgIHRyeToNCiAgICAgICAgICAgIHdoaWxlIG5vdCBmYWlsZWQgYW5kIHNlbGYudXNlcm5hbWUgaXMgTm9uZSBhbmQgdG9rZW5fdHRsID4gMDoNCiAgICAgICAgICAgICAgICB4Ym1jLnNsZWVwKDEwMDApDQogICAgICAgICAgICAgICAgdG9rZW5fdHRsIC09IDENCiAgICAgICAgICAgICAgICBpZiB0b2tlbl90dGwgJSBpbnRlcnZhbCA9PSAwOg0KICAgICAgICAgICAgICAgICAgICBmYWlsZWQgPSBzZWxmLl9hdXRoX3BvbGwoZGV2aWNlKQ0KICAgICAgICAgICAgICAgIHByb2dyZXNzX3dpZHRoID0gaW50KGZsb2F0KHRva2VuX3R0bCAqIDUzMCkgLyBleHBpcnkpDQogICAgICAgICAgICAgICAgcXJfZGlhbG9nLnNldFByb3BlcnR5KCJwcm9ncmVzc193aWR0aCIsIHN0cihwcm9ncmVzc193aWR0aCkpDQogICAgICAgICAgICAgICAgcXJfZGlhbG9nLnNldFByb3BlcnR5KCJleHBpcmVzX2xhYmVsIiwgIGYiRXhwaXJlcyBpbiB7dG9rZW5fdHRsfXMiKQ0KICAgICAgICBmaW5hbGx5Og0KICAgICAgICAgICAgcXJfZGlhbG9nLmNsb3NlKCkNCiAgICAgICAgICAgIGRlbCBxcl9kaWFsb2cNCiAgICAgICAgICAgIHJlbW92ZV9xcihxcl9wYXRoKQ0KICAgICAgICAjIC0tIGVuZCBTZXJlbiBRUiBBdXRoIHBhdGNoIC0tDQo='

# ---------------------------------------------------------------------------
ADDON_NAME  = 'ABUKARIM TOOLS'
HOME        = xbmcvfs.translatePath('special://home/')
ADDONS_DIR  = os.path.join(HOME, 'addons')

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
PATCHES = [
    {
        'addon_id':    'plugin.video.redlight',
        'rel_path':    os.path.join('resources', 'lib', 'modules', 'kodi_utils.py'),
        'old':         (
            "def addon_themes():\n"
            "\treturn [{'name': 'Light', 'value': ('FF434343', 'FF2E2E2E'), 'icon': 'light'}, "
            "{'name': 'Medium', 'value': ('FF373737', 'FF4a4347'), 'icon': 'medium'},\n"
            "\t\t\t{'name': 'Dark', 'value': ('FF1F2020', 'FF4F4F4F'), 'icon': 'dark'}]"
        ),
        'new':         (
            "def addon_themes():\n"
            "\treturn [{'name': 'Dark', 'value': ('FF1F2020', 'FF4F4F4F'), 'icon': 'dark'}]"
        ),
        'description': 'RedLight – window theme locked to Dark only',
        # fallback: if the exact string isn't found (already patched or different
        # version) we fall back to a regex that handles any variant
        'fallback_pattern': r"(def addon_themes\(\):\s*\n\s*return\s*\[).*?(\])",
        'fallback_repl':    (
            r"\g<1>{'name': 'Dark', 'value': ('FF1F2020', 'FF4F4F4F'), 'icon': 'dark'}\g<2>"
        ),
    },
    {
        'addon_id':    'script.tinyppi',
        'rel_path':    os.path.join('resources', 'lib', 'overlay.py'),
        'old':         '_ALLOW_NON_COREELEC = False',
        'new':         '_ALLOW_NON_COREELEC = True',
        'description': 'TinyPPI – _ALLOW_NON_COREELEC enabled',
        'fallback_pattern': r'_ALLOW_NON_COREELEC\s*=\s*False',
        'fallback_repl':    '_ALLOW_NON_COREELEC = True',
    },
    # ------------------------------------------------------------------
    # Patch – RedLight dialogs.py: remove theme selection dialog,
    # silently apply Dark when type='theme' is triggered
    # ------------------------------------------------------------------
    {
        'addon_id':    'plugin.video.redlight',
        'rel_path':    os.path.join('resources', 'lib', 'indexers', 'dialogs.py'),
        'old': (
            "\tif params['type'] == 'theme':\n"
            "\t\tchoices = kodi_utils.addon_themes()\n"
            "\t\tlist_items = [{'line1': i['name'], 'icon': kodi_utils.get_icon(i['icon'], 'themes')} for i in choices]\n"
            "\t\tkwargs = {'items': json.dumps(list_items), 'heading': 'Assign a Theme', 'narrow_window': 'true'}\n"
            "\t\tchoice = kodi_utils.select_dialog(choices, **kwargs)\n"
            "\t\tif choice == None: return\n"
            "\t\twindow_theme, window_theme_contrast, window_theme_name = choice['value'][0][2:], choice['value'][1], choice['name']\n"
            "\t\twindow_theme_opacity = get_setting('redlight.window_theme_opacity', 'CC')\n"
            "\t\tset_setting('window_theme_name', window_theme_name)"
        ),
        'new': (
            "\tif params['type'] == 'theme':\n"
            "\t\t# PATCHED: Dark theme only\n"
            "\t\tdark_theme = kodi_utils.addon_themes()[0]\n"
            "\t\twindow_theme, window_theme_contrast, window_theme_name = dark_theme['value'][0][2:], dark_theme['value'][1], dark_theme['name']\n"
            "\t\twindow_theme_opacity = get_setting('redlight.window_theme_opacity', 'CC')\n"
            "\t\tset_setting('window_theme_name', window_theme_name)"
        ),
        'description': 'RedLight dialogs.py – remove theme picker, auto-apply Dark',
        'fallback_pattern': None,
        'fallback_repl':    None,
        'already_patched_check': 'PATCHED: Dark theme only',
    },
    # ------------------------------------------------------------------
    # Patch – RedLight settings_manager.xml: remove 'Assign Window Theme'
    # clickable item (only Dark theme exists)
    # ------------------------------------------------------------------
    {
        'addon_id':    'plugin.video.redlight',
        'rel_path':    os.path.join('resources', 'skins', 'Default', '1080i', 'settings_manager.xml'),
        'old': (
            '                      <item>\r\n'
            '                          <visible>Container(2000).HasFocus(10)</visible>\r\n'
            '                          <property name="setting_label">Assign Window Theme</property>\r\n'
            '                          <property name="setting_type">action</property>\r\n'
            '                          <property name="setting_value">$INFO[Window(10000).Property(redlight.window_theme_name)]</property>\r\n'
            '                          <property name="setting_description">Choose the theme Red Light will use for custom windows. Choices are Light, Medium and Dark</property>\r\n'
            '                          <onclick>RunPlugin(plugin://plugin.video.redlight/?mode=window_theme_choice&amp;type=theme)</onclick>\r\n'
            '                      </item>\r\n'
        ),
        'new': '',
        'description': 'RedLight settings_manager.xml – remove Assign Window Theme item',
        'fallback_pattern': r'[ \t]*<item>[\s\S]*?<property name="setting_label">Assign Window Theme</property>[\s\S]*?</item>\r?\n',
        'fallback_repl':    '',
        'already_patched_check': None,
        'not_found_ok': True,
    },
    # ------------------------------------------------------------------
    # Patch 3 – properties.py: strip "Dolby Vision " prefix from
    # get_DoviProfileVar() so it returns e.g. "Profile 7 FEL" instead of
    # "Dolby Vision Profile 7 FEL".  The skin uses the DVProfileELVar XML
    # variable to show FEL/MEL colours separately.
    # ------------------------------------------------------------------
    {
        'addon_id':    'script.tinyppi',
        'rel_path':    os.path.join('resources', 'lib', 'properties.py'),
        'old': (
            '        return "Dolby Vision Profile 8.1"\n\n    prof = re.search'
        ),
        'new': (
            '        return "Profile 8.1"\n\n    prof = re.search'
        ),
        'description': 'TinyPPI properties.py – DoviProfileVar strips "Dolby Vision " prefix (fallback)',
        # regex covers all four return statements in get_DoviProfileVar()
        'fallback_pattern': r'"Dolby Vision (Profile [^"]*)"',
        'fallback_repl':    r'"\1"',
    },
    # ------------------------------------------------------------------
    # Patch 4 – monitor.py: replace the entire original KodiMonitor class
    # with the updated version that includes _start_hdr_poll,
    # _poll_hdr_properties, _clear_hdr_properties, and
    # _update_hdr_properties.
    # ------------------------------------------------------------------
    {
        'addon_id':    'script.tinyppi',
        'rel_path':    os.path.join('resources', 'lib', 'monitor.py'),
        'old': (
            'import json\n'
            'import os\n'
            'import sys\n'
            '\n'
            'import xbmc\n'
            'import xbmcaddon\n'
            'import xbmcgui'
        ),
        'new': (
            'import json\n'
            'import os\n'
            'import sys\n'
            'import threading\n'
            '\n'
            'import xbmc\n'
            'import xbmcaddon\n'
            'import xbmcgui'
        ),
        'description': 'TinyPPI monitor.py – add threading import',
        'fallback_pattern': r'(import json\nimport os\nimport sys\n)(\nimport xbmc)',
        'fallback_repl':    r'\1import threading\n\2',
    },
    # ------------------------------------------------------------------
    # Patch 5 – monitor.py: add __init__ poll_thread attribute
    # ------------------------------------------------------------------
    {
        'addon_id':    'script.tinyppi',
        'rel_path':    os.path.join('resources', 'lib', 'monitor.py'),
        'old': (
            '        self.win   = win\n'
            '        self.addon = addon\n'
            '\n'
            '    def onNotification'
        ),
        'new': (
            '        self.win   = win\n'
            '        self.addon = addon\n'
            '        self._poll_thread = None\n'
            '\n'
            '    def onNotification'
        ),
        'description': 'TinyPPI monitor.py – add _poll_thread attribute to __init__',
        'fallback_pattern': r'(self\.win\s+=\s+win\n\s+self\.addon\s+=\s+addon\n)(\n\s+def onNotification)',
        'fallback_repl':    r'\1        self._poll_thread = None\n\2',
    },
    # ------------------------------------------------------------------
    # Patch 6 – monitor.py: replace bare onNotification body with the
    # full version that triggers HDR polling on Player.OnPlay/OnStop
    # ------------------------------------------------------------------
    {
        'addon_id':    'script.tinyppi',
        'rel_path':    os.path.join('resources', 'lib', 'monitor.py'),
        'old': (
            '            _log(f"sender={sender}  method={method}  type={mediatype!r}")\n'
            '\n'
            '        except Exception as exc:\n'
            '            _log(f"Exception in KodiMonitor.onNotification: {exc}", xbmc.LOGERROR)\n'
            '\n'
            '\n'
            '# ---------------------------------------------------------------------------\n'
            '# Entry point  (called by Kodi via the xbmc.service extension point)\n'
            '# ---------------------------------------------------------------------------'
        ),
        'new': (
            '            _log(f"sender={sender}  method={method}  type={mediatype!r}")\n'
            '\n'
            '            if method == "Player.OnPlay":\n'
            '                self._start_hdr_poll()\n'
            '                self._update_hdr_properties()\n'
            '\n'
            '            if method == "Player.OnStop":\n'
            '                self._clear_hdr_properties()\n'
            '\n'
            '        except Exception as exc:\n'
            '            _log(f"Exception in KodiMonitor.onNotification: {exc}", xbmc.LOGERROR)\n'
            '\n'
            '    def _update_hdr_properties(self) -> None:\n'
            '        """Immediately read and publish HDR/DV properties after playback starts."""\n'
            '        xbmc.sleep(3000)  # wait for player to initialise\n'
            '        _addon_path = xbmcaddon.Addon(_ADDON_ID).getAddonInfo("path")\n'
            '        sys.path.insert(0, os.path.join(_addon_path, "resources", "lib"))\n'
            '        try:\n'
            '            from properties import get_HdmiHdrStatusVar, get_DoviProfileVar\n'
            '            hdr  = get_HdmiHdrStatusVar()\n'
            '            dovi = get_DoviProfileVar()\n'
            '            xbmc.executebuiltin(f"SetProperty(HdmiHdrStatusVar,{hdr},Home)")\n'
            '            xbmc.executebuiltin(f"SetProperty(DoviProfileVar,{dovi},Home)")\n'
            '            _log(f"_update_hdr_properties: hdr={hdr!r}  dovi={dovi!r}", xbmc.LOGINFO)\n'
            '        except Exception as exc:\n'
            '            _log(f"_update_hdr_properties failed: {exc}", xbmc.LOGERROR)\n'
            '\n'
            '    def _start_hdr_poll(self) -> None:\n'
            '        """Start a background thread that polls HDR properties for 30 seconds."""\n'
            '        if self._poll_thread and self._poll_thread.is_alive():\n'
            '            return\n'
            '        self._poll_thread = threading.Thread(target=self._poll_hdr_properties, daemon=True)\n'
            '        self._poll_thread.start()\n'
            '\n'
            '    def _poll_hdr_properties(self) -> None:\n'
            '        """Poll every 2 seconds for 30 seconds until DV profile is found."""\n'
            '        _addon_path = xbmcaddon.Addon(_ADDON_ID).getAddonInfo("path")\n'
            '        sys.path.insert(0, os.path.join(_addon_path, "resources", "lib"))\n'
            '        try:\n'
            '            from properties import get_HdmiHdrStatusVar, get_DoviProfileVar\n'
            '            for _ in range(15):  # 15 attempts x 2 seconds = 30 seconds\n'
            '                xbmc.sleep(2000)\n'
            '                hdr  = get_HdmiHdrStatusVar()\n'
            '                dovi = get_DoviProfileVar()\n'
            '                xbmc.executebuiltin(f"SetProperty(HdmiHdrStatusVar,{hdr},Home)")\n'
            '                xbmc.executebuiltin(f"SetProperty(DoviProfileVar,{dovi},Home)")\n'
            '                _log(f"HDR poll: HdmiHdrStatusVar={hdr!r}  DoviProfileVar={dovi!r}", xbmc.LOGINFO)\n'
            '                if dovi:\n'
            '                    _log("DV profile found — stopping poll", xbmc.LOGINFO)\n'
            '                    break\n'
            '        except Exception as exc:\n'
            '            _log(f"_poll_hdr_properties failed: {exc}", xbmc.LOGERROR)\n'
            '\n'
            '    def _clear_hdr_properties(self) -> None:\n'
            '        """Clear HDR properties from Window(Home) when playback stops."""\n'
            '        xbmc.executebuiltin("ClearProperty(HdmiHdrStatusVar,Home)")\n'
            '        xbmc.executebuiltin("ClearProperty(DoviProfileVar,Home)")\n'
            '\n'
            '\n'
            '# ---------------------------------------------------------------------------\n'
            '# Entry point  (called by Kodi via the xbmc.service extension point)\n'
            '# ---------------------------------------------------------------------------'
        ),
        'description': 'TinyPPI monitor.py – add HDR poll/update/clear methods',
        'fallback_pattern': None,
        'fallback_repl':    None,
        # already-patched check: shorter sentinel that only exists post-patch
        'already_patched_check': '_update_hdr_properties',
    },
    # ── Seren QR Auth ──
    {
        'addon_id': 'plugin.video.seren',
        'rel_path': os.path.join('resources', 'lib', 'qr_utils.py'),
        'old': '', 'new': '',
        'description': 'Seren – inject qr_utils.py',
        'inject_file': True,
        'inject_content_b64': _SEREN_QR_UTILS_B64,
        'already_patched_check': 'api.qrserver.com',
    },
    {
        'addon_id': 'plugin.video.seren',
        'rel_path': os.path.join('resources', 'skins', 'Default', '1080i', 'trakt_auth_qr.xml'),
        'old': '', 'new': '',
        'description': 'Seren – inject trakt_auth_qr.xml',
        'inject_file': True,
        'inject_content_b64': _SEREN_XML_B64,
        'already_patched_check': 'trakt_auth_qr',
    },
    {
        'addon_id': 'plugin.video.seren',
        'rel_path': os.path.join('resources', 'lib', 'indexers', 'trakt.py'),
        'old': base64.b64decode(_SEREN_OLD_B64).decode('utf-8'),
        'new': base64.b64decode(_SEREN_NEW_B64).decode('utf-8'),
        'description': 'Seren trakt.py – QR auth dialog',
        'already_patched_check': '# -- Seren QR Auth patch (by ABUKARIM TOOLS) --',
        'fallback_pattern': None, 'fallback_repl': None,
    },
]


# ---------------------------------------------------------------------------
def _log(msg):
    xbmc.log('[AbukarimTools Patcher] %s' % msg, xbmc.LOGINFO)


def _read(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


def _write(path, content):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)


def _apply_patch(patch):
    """
    Apply a single patch dict.
    Returns (success: bool, message: str)
    """
    addon_path = os.path.join(ADDONS_DIR, patch['addon_id'])
    if not os.path.isdir(addon_path):
        return False, '[%s] Addon not found: %s' % (patch['addon_id'], addon_path)

    target = os.path.join(addon_path, patch['rel_path'])
    # inject_file: ينشئ الملف مباشرة قبل أي فحص
    if patch.get('inject_file'):
        b64 = patch.get('inject_content_b64', '')
        inject_content = base64.b64decode(b64).decode('utf-8') if b64 else patch.get('inject_content', '')
        already_check = patch.get('already_patched_check', '')
        if os.path.isfile(target) and already_check and already_check in _read(target):
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

    # Exact match replacement
    if patch['old'] in content:
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
        new_content, n = re.subn(pattern, repl, content, count=1, flags=re.DOTALL)
        if n:
            _write(target, new_content)
            return True, '[%s] Patched OK (regex): %s' % (patch['addon_id'], patch['description'])

    if patch.get('not_found_ok'):
        return True, '[%s] Already patched – skipping.' % patch['addon_id']

    return False, '[%s] Patch string not found in %s' % (patch['addon_id'], patch['rel_path'])


# ---------------------------------------------------------------------------
def _reset_redlight_theme():
    DARK_THEME    = 'CC1F2020'
    DARK_CONTRAST = 'FF4a4347'
    try:
        import sqlite3
        db_path = xbmcvfs.translatePath(
            'special://profile/addon_data/plugin.video.redlight/databases/settings.db'
        )
        if xbmcvfs.exists(db_path):
            con = sqlite3.connect(db_path, timeout=10, isolation_level=None)
            con.execute('PRAGMA synchronous = OFF')
            rows = [
                ('window_theme',             'string', 'CC1F2020', DARK_THEME),
                ('window_theme_contrast',    'string', 'FF4a4347', DARK_CONTRAST),
                ('window_theme_name',        'string', 'Dark',     'Dark'),
                ('window_theme_opacity',     'string', 'CC',       'CC'),
                ('window_theme_opacity_name','string', '80%',      '80%'),
            ]
            for row in rows:
                con.execute('INSERT OR REPLACE INTO settings VALUES (?, ?, ?, ?)', row)
            con.close()
            _log('RedLight settings.db updated to Dark theme')
    except Exception as e:
        _log('settings.db write failed: %s' % e)
    try:
        win = xbmcgui.Window(10000)
        win.setProperty('redlight.window_theme',          DARK_THEME)
        win.setProperty('redlight.window_theme_contrast', DARK_CONTRAST)
        win.setProperty('redlight.window_theme_name',     'Dark')
        win.setProperty('redlight.window_theme_opacity',  'CC')
        win.setProperty('redlight.window_theme_opacity_name', '80%')
        _log('RedLight window properties set to Dark theme')
    except Exception as e:
        _log('Window property write failed: %s' % e)



# ---------------------------------------------------------------------------
def run():
    """Entry point called from default.py router."""
    _log('Starting patch run …')

    results   = []
    succeeded = 0
    failed    = 0

    for patch in PATCHES:
        ok, msg = _apply_patch(patch)
        _log(msg)
        results.append((ok, msg))
        if ok:
            succeeded += 1
        else:
            failed += 1

    # Build summary dialog
    lines = []
    for ok, msg in results:
        icon   = '[COLOR lime]✔[/COLOR]' if ok else '[COLOR red]✘[/COLOR]'
        # strip the leading [addon_id] prefix for display
        display = re.sub(r'^\[.*?\]\s*', '', msg)
        lines.append('%s  %s' % (icon, display))

    summary = '[B]Patch Results[/B][CR][CR]' + '[CR]'.join(lines)
    summary += '[CR][CR]%d succeeded,  %d failed.' % (succeeded, failed)

    DIALOG.ok(ADDON_NAME, summary)
    _log('Patch run complete: %d OK, %d failed.' % (succeeded, failed))

    _reset_redlight_theme()
