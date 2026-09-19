"""检测器基类（插件接口）"""


class Detector:
    """
    所有容器检测器的基类。

    子类需要定义：
        name               —— 检测器名称（用于日志）
        target_extensions  —— 关注的扩展名列表（不含点，小写）
                               当 MagicTable 匹配到的扩展名在其中时，
                               refine() 会被调用。

    子类需要实现：
        refine(file_path, header_hex) -> str | None
            - file_path: 待处理文件的完整路径
            - header_hex: 文件头的十六进制字符串（大写）
            - 返回值: 细化后的扩展名（不含点），或 None 表示不修改
    """

    name = "base"
    target_extensions = []

    @classmethod
    def refine(cls, file_path, header_hex):
        return None