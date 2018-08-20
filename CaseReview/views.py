from flask import render_template, send_from_directory

import os

from . import app, Config
from .databases import CaseRecord, CaseTuple


@app.route('/')
def index():
    config = {
        'colHeaders': CaseTuple.__slots__,
        'renderers': {
            'front': 'markdownRenderer',
            'back': 'markdownRenderer'
        },
        'colWidths': [92, 88, 243, 529, 148, 125, 206]
    }

    return render_template('index.html', title=os.getenv('DATABASE_URI', ''), config=config)


@app.route('/card/<int:card_id>')
def card(card_id):
    record = CaseRecord.query.filter_by(id=card_id).first()
    return render_template('card.html', card=dict(CaseTuple().from_db(record)), show=False)


@app.route('/card/<int:card_id>/show')
def card_show(card_id):
    record = CaseRecord.query.filter_by(id=card_id).first()
    return render_template('card.html', card=dict(CaseTuple().from_db(record)), show=True)


@app.route('/images/<filename>')
def get_image(filename):
    return send_from_directory(Config.IMAGE_DATABASE_FOLDER, filename)
