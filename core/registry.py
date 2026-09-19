"""检测器插件的自动发现与调度"""

import importlib
import inspect
import pkgutil


DETECTOR_PACKAGE = 'detectors'

_registry = []  # 已注册的检测器类


def discover(console=None, package=DETECTOR_PACKAGE):
    """
    扫描 detectors 包下的所有子模块，自动注册 Detector 子类。
    用户新增一个 detectors/xxx.py 文件即可自动被加载。
    """
    global _registry
    _registry = []

    try:
        pkg = importlib.import_module(package)
    except ImportError:
        if console:
            console.warn(f"未找到检测器包 '{package}'，仅使用魔数表。")
        return []

    # 导入基类
    try:
        base_mod = importlib.import_module(f'{package}.base')
    except ImportError:
        if console:
            console.warn(f"未找到 {package}.base，插件系统不可用。")
        return []

    Base = base_mod.Detector

    for _, mod_name, _ in pkgutil.iter_modules(pkg.__path__):
        if mod_name == 'base':
            continue
        try:
            mod = importlib.import_module(f'{package}.{mod_name}')
        except Exception as e:
            if console:
                console.warn(f"加载检测器 '{mod_name}' 失败: {e}")
            continue

        for _, obj in inspect.getmembers(mod, inspect.isclass):
            # 只注册定义在该模块内的 Detector 子类
            if (issubclass(obj, Base)
                    and obj is not Base
                    and obj.__module__ == mod.__name__):
                _registry.append(obj)
                if console:
                    console.notice(f"已加载检测器: {obj.name} -> {obj.target_extensions}")

    return list(_registry)


def list_all():
    return list(_registry)


def refine(matched_ext, file_path, header_hex):
    """
    根据 MagicTable 匹配到的扩展名，调用相应检测器细化。
    返回细化后的扩展名（不含点），若无检测器处理则返回 None。
    """
    if not _registry or matched_ext is None:
        return None
    for det in _registry:
        if matched_ext.lower() in [e.lower() for e in det.target_extensions]:
            try:
                result = det.refine(file_path, header_hex)
            except Exception:
                result = None
            if result:
                return result
    return None