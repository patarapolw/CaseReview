from flask import request, jsonify, Response
from werkzeug.utils import secure_filename

import math
from datetime import datetime
import os
import re
import sqlalchemy.exc

from . import app, db, Config
from .databases import CaseRecord, CaseTuple
from .util import get_url_images_in_text

sort_by = {
    'column': 'modified',
    'desc': True
}


def get_ordering():
    result = getattr(CaseRecord, sort_by['column'])

    if sort_by['desc']:
        return result.desc()
    else:
        return result


@app.route('/api/all/<page_number>')
def all_records(page_number, page_size=10):
    def _filter():
        for srs_record in CaseRecord.query.order_by(get_ordering()):
                yield srs_record

    page_number = int(page_number)

    query = list(_filter())
    total = len(query)

    if page_number < 0:
        page_number = math.ceil(total / page_size) + page_number + 1

    offset = (page_number - 1) * page_size

    records = query[offset:offset + page_size]

    data = [dict(CaseTuple().from_db(record)) for record in records]

    if len(data) == 0:
        data = [dict(CaseTuple().from_db(None))]

    return jsonify({
        'data': data,
        'pages': {
            'from': offset + 1 if total > 0 else 0,
            'to': total if offset + page_size > total else offset + page_size,
            'number': page_number,
            'total': total
        }
    })


@app.route('/api/search/<page_number>', methods=['POST'])
def search(page_number, page_size=10):
    def _search():
        query_string = request.get_json()['q'].lower()

        for srs_record in CaseRecord.query.order_by(get_ordering()):
            front = srs_record.front
            if front:
                for url in get_url_images_in_text(front):
                    front = front.replace(url, ' ')

            back = srs_record.back
            if back:
                for url in get_url_images_in_text(back):
                    back = back.replace(url, ' ')

            if any([query_string in cell.lower()
                    for cell in (front, back, srs_record.tags, srs_record.keywords) if cell]):
                yield srs_record

    page_number = int(page_number)

    query = list(_search())
    total = len(query)

    if page_number < 0:
        page_number = math.ceil(total / page_size) + page_number + 1

    offset = (page_number - 1) * page_size

    records = query[offset:offset + page_size]

    data = [dict(CaseTuple().from_db(record)) for record in records]

    if len(data) == 0:
        data = [dict(CaseTuple().from_db(None))]

    return jsonify({
        'data': data,
        'pages': {
            'from': offset + 1 if total > 0 else 0,
            'to': total if offset + page_size > total else offset + page_size,
            'number': page_number,
            'total': total
        }
    })


@app.route('/api/edit', methods=['POST'])
def edit_record():
    record = request.get_json()
    old_record = CaseRecord.query.filter_by(id=record['id']).first()
    if old_record is None:
        srs_tuple = CaseTuple()
        setattr(srs_tuple, record['fieldName'], record['data'])

        new_record = CaseRecord(**srs_tuple.to_db())

        try:
            db.session.add(new_record)
            db.session.commit()
            record_id = new_record.id
        except sqlalchemy.exc.IntegrityError:
            return Response(status=400)
    else:
        setattr(old_record,
                record['fieldName'],
                CaseTuple.parse(record['fieldName'], record['data']))
        old_record.modified = datetime.now()

        db.session.commit()
        record_id = old_record.id

    return jsonify({
        'id': record_id
    }), 201


@app.route('/api/delete/<int:record_id>', methods=['DELETE'])
def delete_record(record_id):
    srs_record = CaseRecord.query.filter_by(id=record_id).first()
    front = srs_record.front

    db.session.delete(srs_record)
    db.session.commit()

    return jsonify({
        'id': record_id,
        'front': front
    }), 303


@app.route('/api/images/create', methods=['POST'])
def create_image():
    if not os.path.exists(Config.IMAGE_DATABASE_FOLDER):
        os.mkdir(Config.IMAGE_DATABASE_FOLDER)

    if 'file' in request.files:
        file = request.files['file']
        filename = secure_filename(file.filename)
        while os.path.exists(os.path.join(Config.IMAGE_DATABASE_FOLDER, filename)):
            filename_stem, filename_ext = os.path.splitext(filename)
            today_date = datetime.now().isoformat()[:10]

            match_obj = re.search(f'(.*{today_date}-)(\d+)$', filename_stem)
            if match_obj is not None:
                filename_stem = match_obj.group(1) + str(int(match_obj.group(2)) + 1)
            else:
                match_obj = re.search(f'.*{today_date}$', filename_stem)
                if match_obj is not None:
                    filename_stem = filename_stem + '-0'
                else:
                    filename_stem = filename_stem + today_date

            filename = filename_stem + filename_ext

        file.save(os.path.join(Config.IMAGE_DATABASE_FOLDER, filename))

        return jsonify({
            'filename': filename
        }), 201

    return Response(status=304)


@app.route('/api/sort_by/<column>', methods=['POST'])
def new_sort(column):
    if column == sort_by['column']:
        sort_by['desc'] = not sort_by['desc']
    else:
        sort_by['column'] = column

    return Response(status=201)
