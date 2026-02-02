# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_all, collect_submodules

# 收集chromadb所需的数据和二进制文件
datas = []
binaries = []
hiddenimports = [
    'typing_extensions',
    'langchain_openai',
    'langgraph',
    'openai',
    'google.genai',
    'nltk',
    'sentence_transformers',
    'sklearn',
    'langchain_community',
    'pydantic',
    'pydantic.v1',
    'pydantic.deprecated.decorator',
    'tiktoken_ext.openai_public',
    'tiktoken_ext',
    'chromadb.utils.embedding_functions.onnx_mini_lm_l6_v2',
    'customtkinter',
    'tkinter',
    'langchain',
    'langchain_core',
    'langchain_core.tools',
    'langchain_core.agents',
    'langchain_core.messages',
    'langchain_core.prompt_values',
    'langchain_core.prompts',
    'langchain_core.output_parsers',
    'langchain_core.runnables',
    'langchain_core.callbacks',
    'langchain_core.documents',
    'langchain_core.vectorstores',
    'langchain_core.embeddings',
    'langchain_core.language_models',
    'langchain_core.pydantic_v1',
    'langchain.text_splitter',
    'langchain_community.llms',
    'langchain_community.chat_models',
    'langchain_community.embeddings',
    'langchain_community.vectorstores',
    'langchain_community.document_loaders',
    'langchain_community.tools',
    'langchain_community.utilities',
    'langchain_community.vectorstores.chroma',
    'chromadb.api',
    'chromadb.api.models',
    'chromadb.api.types',
    'chromadb.config',
    'chromadb.errors',
    'chromadb.types',
    'chromadb.telemetry',
    'torch',
    'transformers',
    'numpy',
    'requests',
    'yaml',
    'jinja2',
    'fsspec',
    'PIL',
    'pillow',
    'charset_normalizer',
    'idna',
    'certifi',
    'urllib3',
    'click',
    'colorama',
    'filelock',
    'packaging',
    'psutil',
    'pyyaml',
    'six',
    'smart_open',
    'xxhash',
    'regex',
    'tqdm',
    'tokenizers',
    'accelerate',
    'bitsandbytes',
    'peft',
    'trl',
    'datasets',
    'evaluate',
    'rouge_score',
    'seqeval',
    'optimum',
    'diffusers',
    'controlnet_aux',
    'inflect',
    'librosa',
    'sentencepiece',
    'jieba',
    'safetensors',
]

# 收集项目中的数据文件
datas += [
    ('ui', 'ui'),
    ('novel_generator', 'novel_generator'),
    ('config.example.json', '.'),
    ('prompt_definitions.py', '.'),
    ('utils.py', '.'),
    ('config_manager.py', '.'),
    ('embedding_adapters.py', '.'),
    ('llm_adapters.py', '.'),
    ('consistency_checker.py', '.'),
    ('chapter_directory_parser.py', '.'),
    ('tooltips.py', '.'),
]

# 收集chromadb相关资源
tmp_ret = collect_all('chromadb')
datas += tmp_ret[0]
binaries += tmp_ret[1]
hiddenimports += tmp_ret[2]

# 收集customtkinter资源
try:
    import customtkinter
    customtkinter_dir = os.path.dirname(customtkinter.__file__)
    datas.append((customtkinter_dir, 'customtkinter'))
except ImportError:
    pass

# 收集langchain相关模块
for mod in collect_submodules('langchain'):
    if mod not in hiddenimports:
        hiddenimports.append(mod)

for mod in collect_submodules('langchain_community'):
    if mod not in hiddenimports:
        hiddenimports.append(mod)

for mod in collect_submodules('langchain_core'):
    if mod not in hiddenimports:
        hiddenimports.append(mod)

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='AI_NovelGenerator',
    debug=False,  # 设置为False以减少调试信息
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # 设置为False以隐藏控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico'  # 如果有图标文件
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='AI_NovelGenerator'
)