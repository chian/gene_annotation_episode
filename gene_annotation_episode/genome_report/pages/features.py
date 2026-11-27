"""Section 04: per feature, its page of the call and its alternates, then its page of the matches along it."""
from . import feature_matches, feature_page


def draw(sheet, data):
    for feature in data['features']:
        feature_page.draw_feature(sheet, data, feature)
        feature_matches.draw_feature(sheet, data, feature)
