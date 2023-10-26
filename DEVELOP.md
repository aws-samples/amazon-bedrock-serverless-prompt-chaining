## Develop these examples

Setup:

Get virtual env ready:
```
python3 -m venv .venv

source .venv/bin/activate

pip install -r requirements.txt

pip install boto3

(Next time)
source .venv/bin/activate
```

Run webapp locally:
```
docker compose up --build
```

Run functions locally:
```
# Trip planner
python -c 'from agents.trip_planner.hotels_agent import index; print(index.handler({"location": "Paris, France"}, ""))'

python -c 'from agents.trip_planner.restaurants_agent import index; print(index.handler({"location": "Paris, France"}, ""))'

python -c 'from agents.trip_planner.activities_agent import index; print(index.handler({"location": "Paris, France"}, ""))'

# Story writer
python -c 'from agents.story_writer.characters_agent import index; print(index.handler({"story_description": "cowboys in space"}, ""))'

# Movie pitch
python -c 'from agents.movie_pitch.pitch_generator_agent import index; print(index.handler({"movie_description": "cowboys", "temperature": 0.5}, ""))'

python -c 'from agents.movie_pitch.pitch_chooser_agent import index; print(index.handler([{"movie_description": "cowboys", "movie_pitch": "Cowboys in space."}, {"movie_description": "cowboys", "movie_pitch": "Alien cowboys."}, {"movie_description": "cowboys", "movie_pitch": "Time-traveling cowboys."}], ""))'
```

Set up a Weasyprint Lambda layer (for demo purposes only):
```
git clone https://github.com/kotify/cloud-print-utils.git

cd cloud-print-utils

make build/weasyprint-layer-python3.8.zip

aws lambda publish-layer-version \
    --region us-west-2 \
    --layer-name weasyprint \
    --zip-file fileb://build/weasyprint-layer-python3.8.zip \
    --compatible-runtimes "python3.8" \
    --license-info "MIT" \
    --description "fonts and libs required by weasyprint"

aws ssm put-parameter --region us-west-2 \
    --name WeasyprintLambdaLayer \
    --type String \
    --value <value of LayerVersionArn from above command's output>
```

CDK:
```
cdk synth
```
