# -*- coding: utf-8 -*-
"""
Single source of truth for all user-facing strings in ABUKARIM TOOLS.

Each entry maps a numeric Kodi string id to (English, Arabic). The two
resource.language/*/strings.po files are GENERATED from this map by
tools/gen_po.py — never hand-edit the .po files; edit here and regenerate.

Code looks these up with resources.lib.i18n.T(<id>) which calls
Addon.getLocalizedString(<id>) so Kodi serves whichever language the UI
is set to (Arabic .po when the box is Arabic, English otherwise).

ID ranges:
  30001-30049  main menu labels
  30050-30099  first-run / service
  30100-30149  skin installer
  30150-30179  skin switcher
  30180-30219  binary installer
  30220-30259  backup / restore
  30260-30289  tab toggles (DPlex / Korean)
  30290-30319  patcher / auto-patch watchdog
"""

STRINGS = {
    # ---- main menu (30001-30049) ----
    30001: ("Run First-Time Setup",            "\u062a\u0634\u063a\u064a\u0644 \u0627\u0644\u0625\u0639\u062f\u0627\u062f \u0644\u0623\u0648\u0644 \u0645\u0631\u0629"),
    30002: ("Backup/Restore",                  "\u0646\u0633\u062e \u0627\u062d\u062a\u064a\u0627\u0637\u064a / \u0627\u0633\u062a\u0639\u0627\u062f\u0629"),
    30003: ("Skin Selection",                  "\u0627\u062e\u062a\u064a\u0627\u0631 \u0627\u0644\u0648\u0627\u062c\u0647\u0629"),
    30004: ("New Build Tools",                 "\u0623\u062f\u0648\u0627\u062a \u0627\u0644\u0628\u0646\u0627\u0621 \u0627\u0644\u062c\u062f\u064a\u062f"),
    30005: ("Apply Patches",                   "\u062a\u0637\u0628\u064a\u0642 \u0627\u0644\u062a\u0631\u0642\u064a\u0639\u0627\u062a"),
    30006: ("Auto-Patch On Update: On/Off",    "\u0627\u0644\u062a\u0631\u0642\u064a\u0639 \u0627\u0644\u062a\u0644\u0642\u0627\u0626\u064a \u0639\u0646\u062f \u0627\u0644\u062a\u062d\u062f\u064a\u062b: \u062a\u0634\u063a\u064a\u0644/\u0625\u064a\u0642\u0627\u0641"),
    30007: ("Fix Add-on Update Origins",       "\u0625\u0635\u0644\u0627\u062d \u0645\u0635\u0627\u062f\u0631 \u062a\u062d\u062f\u064a\u062b \u0627\u0644\u0625\u0636\u0627\u0641\u0627\u062a"),
    30008: ("OpenWizard",                      "OpenWizard"),
    30009: ("Skin Switcher",                   "\u0645\u0628\u062f\u0644 \u0627\u0644\u0648\u0627\u062c\u0647\u0627\u062a"),
    30010: ("DPlex Tab On/Off",                "\u062a\u0628\u0648\u064a\u0628 DPlex \u062a\u0634\u063a\u064a\u0644/\u0625\u064a\u0642\u0627\u0641"),
    30011: ("Korean Media Tab On/Off",         "\u062a\u0628\u0648\u064a\u0628 \u0627\u0644\u0645\u062d\u062a\u0648\u0649 \u0627\u0644\u0643\u0648\u0631\u064a \u062a\u0634\u063a\u064a\u0644/\u0625\u064a\u0642\u0627\u0641"),

    # ---- first-run / service (30050-30099) ----
    30050: ("Run first-time setup now?\n\nThis installs binaries, offers a backup restore, then opens the Skin Installer.",
            "\u062a\u0634\u063a\u064a\u0644 \u0627\u0644\u0625\u0639\u062f\u0627\u062f \u0644\u0623\u0648\u0644 \u0645\u0631\u0629 \u0627\u0644\u0622\u0646\u061f\n\n\u0633\u064a\u062a\u0645 \u062a\u062b\u0628\u064a\u062a \u0627\u0644\u0645\u0644\u0641\u0627\u062a \u0627\u0644\u062b\u0646\u0627\u0626\u064a\u0629\u060c \u0648\u0639\u0631\u0636 \u0627\u0633\u062a\u0639\u0627\u062f\u0629 \u0646\u0633\u062e\u0629 \u0627\u062d\u062a\u064a\u0627\u0637\u064a\u0629\u060c \u062b\u0645 \u0641\u062a\u062d \u0645\u062b\u0628\u062a \u0627\u0644\u0648\u0627\u062c\u0647\u0627\u062a."),
    30051: ("Run setup",                       "\u062a\u0634\u063a\u064a\u0644 \u0627\u0644\u0625\u0639\u062f\u0627\u062f"),
    30052: ("Cancel",                          "\u0625\u0644\u063a\u0627\u0621"),
    30053: ("Apply Patches failed \u2014 run it from ABUKARIM TOOLS",
            "\u0641\u0634\u0644 \u062a\u0637\u0628\u064a\u0642 \u0627\u0644\u062a\u0631\u0642\u064a\u0639\u0627\u062a \u2014 \u0634\u063a\u0651\u0644\u0647 \u0645\u0646 ABUKARIM TOOLS"),
    30054: ("Skin Installer could not be started.\nYou can run it later from ABUKARIM TOOLS.",
            "\u062a\u0639\u0630\u0631 \u0628\u062f\u0621 \u0645\u062b\u0628\u062a \u0627\u0644\u0648\u0627\u062c\u0647\u0627\u062a.\n\u064a\u0645\u0643\u0646\u0643 \u062a\u0634\u063a\u064a\u0644\u0647 \u0644\u0627\u062d\u0642\u0627\u064b \u0645\u0646 ABUKARIM TOOLS."),
    30055: ("Binary installer failed \u2014 run it from ABUKARIM TOOLS",
            "\u0641\u0634\u0644 \u0645\u062b\u0628\u062a \u0627\u0644\u0645\u0644\u0641\u0627\u062a \u0627\u0644\u062b\u0646\u0627\u0626\u064a\u0629 \u2014 \u0634\u063a\u0651\u0644\u0647 \u0645\u0646 ABUKARIM TOOLS"),
    30056: ("Restore could not be started.\nYou can run it later from ABUKARIM TOOLS \u2192 Backup/Restore.",
            "\u062a\u0639\u0630\u0631 \u0628\u062f\u0621 \u0627\u0644\u0627\u0633\u062a\u0639\u0627\u062f\u0629.\n\u064a\u0645\u0643\u0646\u0643 \u062a\u0634\u063a\u064a\u0644\u0647\u0627 \u0644\u0627\u062d\u0642\u0627\u064b \u0645\u0646 ABUKARIM TOOLS \u2190 \u0646\u0633\u062e \u0627\u062d\u062a\u064a\u0627\u0637\u064a/\u0627\u0633\u062a\u0639\u0627\u062f\u0629."),
    30057: ("Setup is almost complete.\n\nWould you like to restore a previous backup?",
            "\u0627\u0644\u0625\u0639\u062f\u0627\u062f \u0623\u0648\u0634\u0643 \u0639\u0644\u0649 \u0627\u0644\u0627\u0643\u062a\u0645\u0627\u0644.\n\n\u0647\u0644 \u062a\u0631\u064a\u062f \u0627\u0633\u062a\u0639\u0627\u062f\u0629 \u0646\u0633\u062e\u0629 \u0627\u062d\u062a\u064a\u0627\u0637\u064a\u0629 \u0633\u0627\u0628\u0642\u0629\u061f"),
    30058: ("Restore Backup",                  "\u0627\u0633\u062a\u0639\u0627\u062f\u0629 \u0646\u0633\u062e\u0629"),
    30059: ("Skip",                            "\u062a\u062e\u0637\u064a"),

    # ---- skin installer (30100-30149) ----
    30100: ("Connecting\u2026",                "\u062c\u0627\u0631\u064d \u0627\u0644\u0627\u062a\u0635\u0627\u0644\u2026"),
    30101: ("Download cancelled.",             "\u062a\u0645 \u0625\u0644\u063a\u0627\u0621 \u0627\u0644\u062a\u0646\u0632\u064a\u0644."),
    30102: ("Downloading\u2026 %d / %d KB",     "\u062c\u0627\u0631\u064d \u0627\u0644\u062a\u0646\u0632\u064a\u0644\u2026 %d / %d \u0643.\u0628"),
    30103: ("Downloading\u2026 %d KB",          "\u062c\u0627\u0631\u064d \u0627\u0644\u062a\u0646\u0632\u064a\u0644\u2026 %d \u0643.\u0628"),
    30104: ("Verifying\u2026",                  "\u062c\u0627\u0631\u064d \u0627\u0644\u062a\u062d\u0642\u0642\u2026"),
    30105: ("Download incomplete or corrupt. Please try again.",
            "\u0627\u0644\u062a\u0646\u0632\u064a\u0644 \u063a\u064a\u0631 \u0645\u0643\u062a\u0645\u0644 \u0623\u0648 \u062a\u0627\u0644\u0641. \u0627\u0644\u0631\u062c\u0627\u0621 \u0627\u0644\u0645\u062d\u0627\u0648\u0644\u0629 \u0645\u0631\u0629 \u0623\u062e\u0631\u0649."),
    30106: ("Download failed:\n%s",            "\u0641\u0634\u0644 \u0627\u0644\u062a\u0646\u0632\u064a\u0644:\n%s"),
    30107: ("Preparing extraction\u2026",       "\u062c\u0627\u0631\u064d \u0627\u0644\u062a\u062d\u0636\u064a\u0631 \u0644\u0644\u0627\u0633\u062a\u062e\u0631\u0627\u062c\u2026"),
    30108: ("Checking archive integrity\u2026",  "\u062c\u0627\u0631\u064d \u0627\u0644\u062a\u062d\u0642\u0642 \u0645\u0646 \u0633\u0644\u0627\u0645\u0629 \u0627\u0644\u0623\u0631\u0634\u064a\u0641\u2026"),
    30109: ("ZIP integrity check failed.\nFirst bad file: %s",
            "\u0641\u0634\u0644 \u0641\u062d\u0635 \u0633\u0644\u0627\u0645\u0629 \u0627\u0644\u0645\u0644\u0641 \u0627\u0644\u0645\u0636\u063a\u0648\u0637.\n\u0623\u0648\u0644 \u0645\u0644\u0641 \u062a\u0627\u0644\u0641: %s"),
    30110: ("Extraction cancelled.",           "\u062a\u0645 \u0625\u0644\u063a\u0627\u0621 \u0627\u0644\u0627\u0633\u062a\u062e\u0631\u0627\u062c."),
    30111: ("Extraction error: size mismatch for\n%s",
            "\u062e\u0637\u0623 \u0641\u064a \u0627\u0644\u0627\u0633\u062a\u062e\u0631\u0627\u062c: \u0639\u062f\u0645 \u062a\u0637\u0627\u0628\u0642 \u0627\u0644\u062d\u062c\u0645 \u0644\u0640\n%s"),
    30112: ("Installing\u2026",                 "\u062c\u0627\u0631\u064d \u0627\u0644\u062a\u062b\u0628\u064a\u062a\u2026"),
    30113: ("Done.",                           "\u062a\u0645."),
    30114: ("The downloaded file is not a valid ZIP archive.",
            "\u0627\u0644\u0645\u0644\u0641 \u0627\u0644\u0645\u064f\u0646\u0632\u0651\u0644 \u0644\u064a\u0633 \u0623\u0631\u0634\u064a\u0641 ZIP \u0635\u0627\u0644\u062d\u0627\u064b."),
    30115: ("Extraction failed:\n%s",          "\u0641\u0634\u0644 \u0627\u0644\u0627\u0633\u062a\u062e\u0631\u0627\u062c:\n%s"),
    30116: ("Enabling %s\u2026",                "\u062c\u0627\u0631\u064d \u062a\u0641\u0639\u064a\u0644 %s\u2026"),
    30117: ("Could not enable %s. Try selecting it manually in Settings.",
            "\u062a\u0639\u0630\u0631 \u062a\u0641\u0639\u064a\u0644 %s. \u062d\u0627\u0648\u0644 \u0627\u062e\u062a\u064a\u0627\u0631\u0647 \u064a\u062f\u0648\u064a\u0627\u064b \u0645\u0646 \u0627\u0644\u0625\u0639\u062f\u0627\u062f\u0627\u062a."),
    30118: ("Applying %s\u2026",                "\u062c\u0627\u0631\u064d \u062a\u0637\u0628\u064a\u0642 %s\u2026"),
    30119: ("%s was installed but could not be selected automatically.\nSelect it manually from Settings > Interface > Skin.",
            "\u062a\u0645 \u062a\u062b\u0628\u064a\u062a %s \u0644\u0643\u0646 \u062a\u0639\u0630\u0631 \u0627\u062e\u062a\u064a\u0627\u0631\u0647 \u062a\u0644\u0642\u0627\u0626\u064a\u0627\u064b.\n\u0627\u062e\u062a\u0631\u0647 \u064a\u062f\u0648\u064a\u0627\u064b \u0645\u0646 \u0627\u0644\u0625\u0639\u062f\u0627\u062f\u0627\u062a > \u0627\u0644\u0648\u0627\u062c\u0647\u0629 > \u0627\u0644\u0645\u0638\u0647\u0631."),
    30120: ("No ZIP URL found for this skin.",
            "\u0644\u0645 \u064a\u064f\u0639\u062b\u0631 \u0639\u0644\u0649 \u0631\u0627\u0628\u0637 ZIP \u0644\u0647\u0630\u0647 \u0627\u0644\u0648\u0627\u062c\u0647\u0629."),
    30121: ("This skin is already installed.\nReinstall %s?",
            "\u0647\u0630\u0647 \u0627\u0644\u0648\u0627\u062c\u0647\u0629 \u0645\u062b\u0628\u062a\u0629 \u0628\u0627\u0644\u0641\u0639\u0644.\n\u0625\u0639\u0627\u062f\u0629 \u062a\u062b\u0628\u064a\u062a %s\u061f"),
    30122: ("Install %s?",                      "\u062a\u062b\u0628\u064a\u062a %s\u061f"),
    30123: ("Network error:\n%s",              "\u062e\u0637\u0623 \u0641\u064a \u0627\u0644\u0634\u0628\u0643\u0629:\n%s"),
    30124: ("The feed returned invalid JSON.", "\u0623\u0631\u062c\u0639 \u0627\u0644\u0645\u0635\u062f\u0631 JSON \u063a\u064a\u0631 \u0635\u0627\u0644\u062d."),
    30125: ("Feed error:\n%s",                 "\u062e\u0637\u0623 \u0641\u064a \u0627\u0644\u0645\u0635\u062f\u0631:\n%s"),
    30126: ("\u2713 %s installed successfully.",
            "\u2713 \u062a\u0645 \u062a\u062b\u0628\u064a\u062a %s \u0628\u0646\u062c\u0627\u062d."),

    # ---- skin switcher (30150-30179) ----
    30150: ("No installed skins found.",       "\u0644\u0645 \u064a\u064f\u0639\u062b\u0631 \u0639\u0644\u0649 \u0648\u0627\u062c\u0647\u0627\u062a \u0645\u062b\u0628\u062a\u0629."),
    30151: ("Choose a skin",                   "\u0627\u062e\u062a\u0631 \u0648\u0627\u062c\u0647\u0629"),

    # ---- binary installer (30180-30219) ----
    30180: ("Platform: [B]%s[/B][CR]Repo: [B]%s[/B][CR][CR]Install the following binary add-ons?[CR][CR]%s",
            "\u0627\u0644\u0645\u0646\u0635\u0629: [B]%s[/B][CR]\u0627\u0644\u0645\u0633\u062a\u0648\u062f\u0639: [B]%s[/B][CR][CR]\u062a\u062b\u0628\u064a\u062a \u0627\u0644\u0625\u0636\u0627\u0641\u0627\u062a \u0627\u0644\u062b\u0646\u0627\u0626\u064a\u0629 \u0627\u0644\u062a\u0627\u0644\u064a\u0629\u061f[CR][CR]%s"),
    30181: ("Checking repository\u2026",        "\u062c\u0627\u0631\u064d \u0627\u0644\u062a\u062d\u0642\u0642 \u0645\u0646 \u0627\u0644\u0645\u0633\u062a\u0648\u062f\u0639\u2026"),
    30182: ("Binary add-ons: repo %s unreachable",
            "\u0627\u0644\u0625\u0636\u0627\u0641\u0627\u062a \u0627\u0644\u062b\u0646\u0627\u0626\u064a\u0629: \u0627\u0644\u0645\u0633\u062a\u0648\u062f\u0639 %s \u063a\u064a\u0631 \u0645\u062a\u0627\u062d"),
    30183: ("[COLOR red]\u2718[/COLOR]  Could not reach [B]%s[/B].[CR][CR]Check your internet connection and that the repo is available for your platform.",
            "[COLOR red]\u2718[/COLOR]  \u062a\u0639\u0630\u0631 \u0627\u0644\u0648\u0635\u0648\u0644 \u0625\u0644\u0649 [B]%s[/B].[CR][CR]\u062a\u062d\u0642\u0642 \u0645\u0646 \u0627\u062a\u0635\u0627\u0644\u0643 \u0628\u0627\u0644\u0625\u0646\u062a\u0631\u0646\u062a \u0648\u0645\u0646 \u062a\u0648\u0641\u0631 \u0627\u0644\u0645\u0633\u062a\u0648\u062f\u0639 \u0644\u0645\u0646\u0635\u062a\u0643."),
    30184: ("Installing [B]%s[/B]\u2026",       "\u062c\u0627\u0631\u064d \u062a\u062b\u0628\u064a\u062a [B]%s[/B]\u2026"),
    30185: ("[COLOR lime]\u2714[/COLOR]  %s \u2013 already installed",
            "[COLOR lime]\u2714[/COLOR]  %s \u2013 \u0645\u062b\u0628\u062a \u0628\u0627\u0644\u0641\u0639\u0644"),
    30186: ("[COLOR lime]\u2714[/COLOR]  %s \u2013 installed OK",
            "[COLOR lime]\u2714[/COLOR]  %s \u2013 \u062a\u0645 \u0627\u0644\u062a\u062b\u0628\u064a\u062a"),
    30187: ("[COLOR red]\u2718[/COLOR]  %s \u2013 install failed",
            "[COLOR red]\u2718[/COLOR]  %s \u2013 \u0641\u0634\u0644 \u0627\u0644\u062a\u062b\u0628\u064a\u062a"),
    30188: ("Binary add-ons: %d OK, %d failed",
            "\u0627\u0644\u0625\u0636\u0627\u0641\u0627\u062a \u0627\u0644\u062b\u0646\u0627\u0626\u064a\u0629: %d \u0646\u062c\u062d\u060c %d \u0641\u0634\u0644"),
    30189: ("Binary add-ons installed (%d/%d)",
            "\u062a\u0645 \u062a\u062b\u0628\u064a\u062a \u0627\u0644\u0625\u0636\u0627\u0641\u0627\u062a \u0627\u0644\u062b\u0646\u0627\u0626\u064a\u0629 (%d/%d)"),
    30190: ("[B]Binary Install Results[/B] ([I]%s[/I])[CR][CR]",
            "[B]\u0646\u062a\u0627\u0626\u062c \u062a\u062b\u0628\u064a\u062a \u0627\u0644\u0645\u0644\u0641\u0627\u062a \u0627\u0644\u062b\u0646\u0627\u0626\u064a\u0629[/B] ([I]%s[/I])[CR][CR]"),
    30191: ("[CR][CR]%d succeeded,  %d failed.",
            "[CR][CR]%d \u0646\u062c\u062d\u060c  %d \u0641\u0634\u0644."),

    # ---- backup / restore (30220-30259) ----
    30220: ("Collecting files\u2026",          "\u062c\u0627\u0631\u064d \u062c\u0645\u0639 \u0627\u0644\u0645\u0644\u0641\u0627\u062a\u2026"),
    30221: ("No files found to back up.",      "\u0644\u0627 \u062a\u0648\u062c\u062f \u0645\u0644\u0641\u0627\u062a \u0644\u0644\u0646\u0633\u062e \u0627\u0644\u0627\u062d\u062a\u064a\u0627\u0637\u064a."),
    30222: ("Backup cancelled.",               "\u062a\u0645 \u0625\u0644\u063a\u0627\u0621 \u0627\u0644\u0646\u0633\u062e \u0627\u0644\u0627\u062d\u062a\u064a\u0627\u0637\u064a."),
    30223: ("Backup complete!\n\n%d files saved to:\n%s",
            "\u0627\u0643\u062a\u0645\u0644 \u0627\u0644\u0646\u0633\u062e \u0627\u0644\u0627\u062d\u062a\u064a\u0627\u0637\u064a!\n\n\u062a\u0645 \u062d\u0641\u0638 %d \u0645\u0644\u0641 \u0641\u064a:\n%s"),
    30224: ("Backup failed!\n%s",              "\u0641\u0634\u0644 \u0627\u0644\u0646\u0633\u062e \u0627\u0644\u0627\u062d\u062a\u064a\u0627\u0637\u064a!\n%s"),
    30225: ("Select backup ZIP to restore",    "\u0627\u062e\u062a\u0631 \u0645\u0644\u0641 \u0627\u0644\u0646\u0633\u062e\u0629 \u0627\u0644\u0627\u062d\u062a\u064a\u0627\u0637\u064a\u0629 (ZIP) \u0644\u0644\u0627\u0633\u062a\u0639\u0627\u062f\u0629"),
    30226: ("Restoring\u2026",                  "\u062c\u0627\u0631\u064d \u0627\u0644\u0627\u0633\u062a\u0639\u0627\u062f\u0629\u2026"),
    30227: ("Restore cancelled (partial restore may have occurred).",
            "\u062a\u0645 \u0625\u0644\u063a\u0627\u0621 \u0627\u0644\u0627\u0633\u062a\u0639\u0627\u062f\u0629 (\u0642\u062f \u062a\u0643\u0648\u0646 \u062a\u0645\u062a \u0627\u0633\u062a\u0639\u0627\u062f\u0629 \u062c\u0632\u0626\u064a\u0629)."),
    30228: ("Restore complete! %d files restored.\n\nguisettings.xml will be applied on next boot.\n\nPlease restart Kodi manually for the changes to take effect.",
            "\u0627\u0643\u062a\u0645\u0644\u062a \u0627\u0644\u0627\u0633\u062a\u0639\u0627\u062f\u0629! \u062a\u0645\u062a \u0627\u0633\u062a\u0639\u0627\u062f\u0629 %d \u0645\u0644\u0641.\n\n\u0633\u064a\u064f\u0637\u0628\u0651\u0642 guisettings.xml \u0639\u0646\u062f \u0627\u0644\u0625\u0642\u0644\u0627\u0639 \u0627\u0644\u062a\u0627\u0644\u064a.\n\n\u0627\u0644\u0631\u062c\u0627\u0621 \u0625\u0639\u0627\u062f\u0629 \u062a\u0634\u063a\u064a\u0644 Kodi \u064a\u062f\u0648\u064a\u0627\u064b \u0644\u062a\u0637\u0628\u064a\u0642 \u0627\u0644\u062a\u063a\u064a\u064a\u0631\u0627\u062a."),
    30229: ("Restore failed!\n%s",             "\u0641\u0634\u0644\u062a \u0627\u0644\u0627\u0633\u062a\u0639\u0627\u062f\u0629!\n%s"),
    30231: ("This will overwrite existing addon_data files, guisettings.xml, and keymaps.\n\nContinue with restore?",
            "\u0633\u064a\u0624\u062f\u064a \u0647\u0630\u0627 \u0625\u0644\u0649 \u0627\u0644\u0643\u062a\u0627\u0628\u0629 \u0641\u0648\u0642 \u0645\u0644\u0641\u0627\u062a addon_data \u0648guisettings.xml \u0648keymaps \u0627\u0644\u062d\u0627\u0644\u064a\u0629.\n\n\u0627\u0644\u0645\u062a\u0627\u0628\u0639\u0629 \u0645\u0639 \u0627\u0644\u0627\u0633\u062a\u0639\u0627\u062f\u0629\u061f"),

    # ---- tab toggles (30260-30289) ----
    30260: ("[COLOR red]\u2718[/COLOR]  Missing bundled file:[CR][I]%s[/I]",
            "[COLOR red]\u2718[/COLOR]  \u0645\u0644\u0641 \u0645\u0631\u0641\u0642 \u0645\u0641\u0642\u0648\u062f:[CR][I]%s[/I]"),
    30261: ("[COLOR lime]ENABLED[/COLOR]",     "[COLOR lime]\u0645\u064f\u0641\u0639\u0651\u0644[/COLOR]"),
    30262: ("[COLOR red]DISABLED[/COLOR]",     "[COLOR red]\u0645\u0639\u0637\u0651\u0644[/COLOR]"),
    30263: ("[COLOR gray]UNKNOWN[/COLOR]",     "[COLOR gray]\u063a\u064a\u0631 \u0645\u0639\u0631\u0648\u0641[/COLOR]"),
    30264: ("%s Tab  \u2013  currently %s",     "\u062a\u0628\u0648\u064a\u0628 %s  \u2013  \u0627\u0644\u062d\u0627\u0644\u0629 %s"),
    30265: ("[COLOR lime]Enable[/COLOR]  %s tab",
            "[COLOR lime]\u062a\u0641\u0639\u064a\u0644[/COLOR]  \u062a\u0628\u0648\u064a\u0628 %s"),
    30266: ("[COLOR red]Disable[/COLOR]  %s tab",
            "[COLOR red]\u062a\u0639\u0637\u064a\u0644[/COLOR]  \u062a\u0628\u0648\u064a\u0628 %s"),
    30267: ("This will %s the %s tab and[CR][B]restart Kodi[/B] to apply the change.[CR][CR]Continue?",
            "\u0633\u064a\u0624\u062f\u064a \u0647\u0630\u0627 \u0625\u0644\u0649 %s \u062a\u0628\u0648\u064a\u0628 %s \u0648[CR][B]\u0625\u0639\u0627\u062f\u0629 \u062a\u0634\u063a\u064a\u0644 Kodi[/B] \u0644\u062a\u0637\u0628\u064a\u0642 \u0627\u0644\u062a\u063a\u064a\u064a\u0631.[CR][CR]\u0645\u062a\u0627\u0628\u0639\u0629\u061f"),
    30268: ("[COLOR lime]enable[/COLOR]",      "[COLOR lime]\u062a\u0641\u0639\u064a\u0644[/COLOR]"),
    30269: ("[COLOR red]disable[/COLOR]",      "[COLOR red]\u062a\u0639\u0637\u064a\u0644[/COLOR]"),
    30270: ("Apply && Restart",                "\u062a\u0637\u0628\u064a\u0642 \u0648\u0625\u0639\u0627\u062f\u0629 \u062a\u0634\u063a\u064a\u0644"),
    30271: ("[COLOR red]\u2718[/COLOR]  Failed to write:[CR][I]%s[/I][CR][CR]%s",
            "[COLOR red]\u2718[/COLOR]  \u0641\u0634\u0644 \u0627\u0644\u0643\u062a\u0627\u0628\u0629:[CR][I]%s[/I][CR][CR]%s"),
    30272: ("%s tab %s \u2013 restarting Kodi\u2026",
            "\u062a\u0628\u0648\u064a\u0628 %s %s \u2013 \u062c\u0627\u0631\u064d \u0625\u0639\u0627\u062f\u0629 \u062a\u0634\u063a\u064a\u0644 Kodi\u2026"),
    30273: ("enabled",                         "\u0645\u064f\u0641\u0639\u0651\u0644"),
    30274: ("disabled",                        "\u0645\u0639\u0637\u0651\u0644"),

    # ---- patcher / auto-patch (30290-30319) ----
    30290: ("Patches re-applied after add-on update",
            "\u0623\u064f\u0639\u064a\u062f \u062a\u0637\u0628\u064a\u0642 \u0627\u0644\u062a\u0631\u0642\u064a\u0639\u0627\u062a \u0628\u0639\u062f \u062a\u062d\u062f\u064a\u062b \u0627\u0644\u0625\u0636\u0627\u0641\u0629"),
    30291: ("Auto-patching is now [B]ON[/B].[CR][CR]Patches are re-applied automatically whenever a patched add-on is updated or reinstalled.",
            "\u0627\u0644\u062a\u0631\u0642\u064a\u0639 \u0627\u0644\u062a\u0644\u0642\u0627\u0626\u064a \u0627\u0644\u0622\u0646 [B]\u0645\u064f\u0641\u0639\u0651\u0644[/B].[CR][CR]\u062a\u064f\u0639\u0627\u062f \u0627\u0644\u062a\u0631\u0642\u064a\u0639\u0627\u062a \u062a\u0644\u0642\u0627\u0626\u064a\u0627\u064b \u0643\u0644\u0645\u0627 \u062a\u0645 \u062a\u062d\u062f\u064a\u062b \u0623\u0648 \u0625\u0639\u0627\u062f\u0629 \u062a\u062b\u0628\u064a\u062a \u0625\u0636\u0627\u0641\u0629 \u0645\u064f\u0631\u0642\u0651\u0639\u0629."),
    30292: ("Auto-patching is now [B]OFF[/B].[CR][CR]Patches will no longer be re-applied automatically after an add-on update - use Apply Patches manually.",
            "\u0627\u0644\u062a\u0631\u0642\u064a\u0639 \u0627\u0644\u062a\u0644\u0642\u0627\u0626\u064a \u0627\u0644\u0622\u0646 [B]\u0645\u0639\u0637\u0651\u0644[/B].[CR][CR]\u0644\u0646 \u062a\u064f\u0639\u0627\u062f \u0627\u0644\u062a\u0631\u0642\u064a\u0639\u0627\u062a \u062a\u0644\u0642\u0627\u0626\u064a\u0627\u064b \u0628\u0639\u062f \u062a\u062d\u062f\u064a\u062b \u0627\u0644\u0625\u0636\u0627\u0641\u0629 - \u0627\u0633\u062a\u062e\u062f\u0645 \u062a\u0637\u0628\u064a\u0642 \u0627\u0644\u062a\u0631\u0642\u064a\u0639\u0627\u062a \u064a\u062f\u0648\u064a\u0627\u064b."),
    30300: ("[B]Downloading:[/B] %s",         "[B]جارٍ التنزيل:[/B] %s"),
    30301: ("Please Wait",                     "الرجاء الانتظار"),
    30302: ("Installing Dependencies",         "جارٍ تثبيت الاعتماديات"),
    30303: ("[B]Installing:[/B] %s",           "[B]جارٍ التثبيت:[/B] %s"),

    # ---- skin selection windows (portal / select_repo XML) (30320-30339) ----
    30320: ("SKIN SELECTION",                  "اختيار الواجهة"),
    30321: ("Select a skin to install · Press Back to exit",
            "اختر واجهة لتثبيتها · اضغط رجوع للخروج"),
    30322: ("Select Repository",               "اختر المستودع"),
    30323: ("OK to select  ·  Back to cancel",
            "موافق للاختيار  ·  رجوع للإلغاء"),
    30324: ("ABUKARIM PORTAL V2",              "بوابة أبوكريم V2"),
    30325: ("Selected Skin",                   "الواجهة المختارة"),
}
