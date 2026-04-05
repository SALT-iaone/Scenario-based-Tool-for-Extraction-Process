# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec ファイル
# 直接実行: pyinstaller STEP.spec

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'mysql.connector',
        'mysql.connector.locales',
        'mysql.connector.locales.eng',
        'mysql.connector.locales.eng.client_error',
        'mysql.connector.plugins',
        'mysql.connector.plugins.mysql_native_password',
        'sshtunnel',
        'paramiko',
        'paramiko.transport',
        'paramiko.auth_handler',
        'paramiko.sftp_client',
        'paramiko.rsakey',
        'paramiko.ed25519key',
        'paramiko.ecdsakey',
        'cryptography',
        'cryptography.hazmat.primitives.asymmetric.padding',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='STEP',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,   # ウィンドウアプリ（ターミナルなし）
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='STEP',
)

# Mac: .app バンドル
app = BUNDLE(
    coll,
    name='STEP.app',
    icon=None,
    bundle_identifier='com.localapp.steptool',
    info_plist={
        'CFBundleName': 'S.T.E.P. - Scenario-based Tool for Extraction Process',
        'CFBundleDisplayName': 'S.T.E.P. - Scenario-based Tool for Extraction Process',
        'CFBundleVersion': '2.2.0',
        'CFBundleShortVersionString': '2.2.0',
        'NSHighResolutionCapable': True,
        'LSMinimumSystemVersion': '10.13.0',
    },
)
