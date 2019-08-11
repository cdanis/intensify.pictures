#!/usr/bin/python3

from flask import Flask, render_template, url_for, request, jsonify, abort, send_from_directory
from werkzeug.utils import secure_filename
from PIL import Image
import glob
import itertools
import math
import os
import random
import secrets
import subprocess
import tempfile

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

OUTPUT_FOLDER = './intensified'

# TODO: investigate why embedding in Discord via URL doesn't animate.


# TODO: make the canonical URLs end in .gif (maybe 301 to there?)
@app.route('/i/<ident>')
def image(ident):
    if not ident.endswith('.gif'):
        ident = ident + '.gif'
    return send_from_directory(OUTPUT_FOLDER, ident, as_attachment=False, mimetype='image/gif')


def _generate_crops(num_frames, input_fnames, *, max_offset=10):
    for fname in itertools.islice(itertools.cycle(input_fnames), num_frames):
        x = random.randint(0, max_offset)
        y = random.randint(0, max_offset)
        yield from ['--crop', f'{x},{y}+-{max_offset-x}x-{max_offset-y}', fname]


def _generate_gifsicle_command(input_fnames, output_fname, *, max_offset=10):
    # TODO: side-shaving will not be appropriate for all images.  need modes.
    # TODO: this doesn't quite work on animated gifs.  it doesn't preserve frame delay,
    # which often means the output looks bad, even in the cases when there was a uniform
    # frame delay to begin with.
    num_input_frames = len(input_fnames)
    # Always produce at least 10 output frames -- but for animated input, round up to
    # a multiple of the input.
    num_frames = (
        num_input_frames
        if num_input_frames >= 10
        else num_input_frames * math.ceil(10 / num_input_frames)
    )
    return itertools.chain(
        ['/usr/bin/gifsicle', '--no-logical-screen', '--disposal=bg', '-lforever', '-d5'],
        _generate_crops(num_frames, input_fnames, max_offset=max_offset),
        ['-O3', '-o', output_fname],
    )


@app.route('/upload', methods=['POST'])
def upload():
    def _random_id():
        # 8 bytes => expected collision after 2^(8*8/2) = 2^32 ~ 4.3bil images
        # but with reasonably short IDs (11 chars in URL)
        return secrets.token_urlsafe(8)

    UPLOAD_FOLDER = './uploads'
    if 'files[]' not in request.files:
        abort(400)

    file = request.files['files[]']
    rando = _random_id()
    uploaded_image = os.path.join(UPLOAD_FOLDER, f'{rando}-{secure_filename(file.filename)}')
    intensified_image = os.path.join(OUTPUT_FOLDER, rando) + '.gif'
    file.save(uploaded_image)
    with tempfile.TemporaryDirectory(prefix="intens") as tmpdir:
        # TODO check if we got a gif already
        # TODO do we want to have a maximum resolution?  (and then downscale?)
        img = Image.open(uploaded_image)
        convert_cmd = ['/usr/bin/convert', uploaded_image]
        if img.width > 500:
            convert_cmd.extend(['-resize', '500'])
        convert_cmd.append('gif:-')
        convert = subprocess.Popen(convert_cmd, stdout=subprocess.PIPE)
        # Exploding a single frame file DTRT.
        explode = subprocess.Popen(
            ['/usr/bin/gifsicle', '--explode', '-', '-o', os.path.join(tmpdir, "explo")],
            stdin=convert.stdout,
        )
        explode.communicate()
        frames = sorted(glob.glob(os.path.join(tmpdir, "explo.*")))

        subprocess.run(_generate_gifsicle_command(frames, intensified_image))
    return jsonify({'result': url_for('image', ident=f'{rando}.gif')})


@app.route('/')
def main():
    return render_template('index.html', endpoint=url_for('upload'))
