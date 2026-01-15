from vitrina.uapi.enums import UdtsCatalogEnum


class CatalogConverter:
    regex = "|".join([catalog.value for catalog in UdtsCatalogEnum])

    def to_python(self, value: str) -> UdtsCatalogEnum:
        return UdtsCatalogEnum(value)

    def to_url(self, value: UdtsCatalogEnum) -> str:
        return value.value
