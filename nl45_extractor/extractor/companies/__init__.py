from extractor.companies.new_india import parse_new_india
from extractor.companies.aditya_birla import parse_aditya_birla
from extractor.companies.icici_lombard import parse_icici_lombard

PARSER_REGISTRY = {
    "parse_new_india":    parse_new_india,
    "parse_aditya_birla": parse_aditya_birla,
    "parse_icici_lombard": parse_icici_lombard,
}
