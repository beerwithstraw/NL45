from extractor.companies.new_india import parse_new_india
from extractor.companies.aditya_birla import parse_aditya_birla

PARSER_REGISTRY = {
    "parse_new_india":    parse_new_india,
    "parse_aditya_birla": parse_aditya_birla,
}
