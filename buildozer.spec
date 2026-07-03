[app]
title = LG IR Remote
package.name = lgremote
package.domain = org.shahram

source.dir = .
source.include_exts = py,png,jpg,kv,atlas

version = 1.0

requirements = python3,kivy

orientation = portrait
fullscreen = 0

# Android permissions - TRANSMIT_IR is required for ConsumerIrManager
android.permissions = TRANSMIT_IR

# Feature declaration for consumer IR hardware (not required, so app still
# installs on phones without an IR blaster, but declares intent to use it)
android.add_uses_feature = android.hardware.consumerir

android.api = 33
android.minapi = 21
android.ndk = 25b
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
