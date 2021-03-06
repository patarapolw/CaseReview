import random
from datetime import datetime

from .databases import CaseRecord
from .tags import tag_reader


def iter_quiz(is_due=True, tag=None):
    def _filter_is_due(srs_record):
        if is_due is None:
            return True
        elif is_due is True:
            if not srs_record.next_review or srs_record.next_review < datetime.now():
                return True
        else:
            if srs_record.next_review is None:
                return True
        return False

    def _filter_tag(srs_record):
        if not tag:
            return True
        elif tag in tag_reader(srs_record.tags):
            return True
        else:
            return False

    def _filter():
        for srs_record in CaseRecord.query.order_by(CaseRecord.modified.desc()):
            if all((_filter_is_due(srs_record),
                    _filter_tag(srs_record))):
                yield srs_record

    all_records = list(_filter())
    random.shuffle(all_records)

    return iter(all_records)
