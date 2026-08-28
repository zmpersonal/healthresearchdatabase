#!/usr/bin/env python3
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[1]
SCORES=ROOT/'score'
ASSETS=ROOT/'assets'
SCORE_IMG=ASSETS/'scores'
SCORES.mkdir(exist_ok=True);SCORE_IMG.mkdir(parents=True,exist_ok=True)

def band(score):
    if score>=90:return 'Exceptional alignment'
    if score>=75:return 'Strong alignment'
    if score>=60:return 'Solid foundation'
    if score>=45:return 'Mixed habits'
    return 'Biggest upside'

def font(size,bold=False,serif=False):
    paths=[]
    if serif:
        paths=['/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf','/usr/share/fonts/truetype/liberation2/LiberationSerif-Regular.ttf']
    elif bold:
        paths=['/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf','/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf']
    else:
        paths=['/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf','/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf']
    for p in paths:
        try:return ImageFont.truetype(p,size)
        except:pass
    return ImageFont.load_default()

def draw_centered(draw,text,y,f,fill,w=1200):
    box=draw.textbbox((0,0),text,font=f);x=(w-(box[2]-box[0]))/2;draw.text((x,y),text,font=f,fill=fill)

def make_score_img(score,path):
    im=Image.new('RGB',(1200,630),'#102128');d=ImageDraw.Draw(im)
    d.ellipse((850,-190,1370,330),outline='#24454a',width=2);d.ellipse((900,-140,1320,280),outline='#1a3b40',width=2)
    d.text((72,58),'HEALTH RESEARCH DATABASE',font=font(20,True),fill='#8ea6aa')
    d.text((72,125),str(score),font=font(210,serif=True),fill='#dff2ec')
    d.text((360,275),'/ 100',font=font(28,True),fill='#789096')
    d.text((72,375),band(score),font=font(46,serif=True),fill='#ffffff')
    d.text((72,455),'Can you beat my Healthspan Habits Score?',font=font(28),fill='#a9bbc0')
    d.line((72,535,1128,535),fill='#30484f',width=2)
    d.text((72,560),'HealthResearchDatabase.com',font=font(19,True),fill='#789096')
    im.save(path,optimize=True)

def page(score):
    b=band(score)
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{score}/100 Healthspan Habits Score | Health Research Database</title><meta name="description" content="A Healthspan Habits Score of {score}/100. Take the same 10-question test and see if you can beat it."><link rel="canonical" href="https://healthresearchdatabase.com/score/{score}/"><meta property="og:title" content="I scored {score}/100. Can you beat me?"><meta property="og:description" content="Take the same 10-question Healthspan Habits Test and compare your score."><meta property="og:type" content="website"><meta property="og:url" content="https://healthresearchdatabase.com/score/{score}/"><meta property="og:image" content="https://healthresearchdatabase.com/assets/scores/score-{score}.png"><meta name="twitter:card" content="summary_large_image"><meta name="theme-color" content="#102128"><link rel="stylesheet" href="/assets/site.css"></head><body class="score-page">
<header class="site-header"><div class="wrap header-inner"><a class="brand" href="/"><span class="brand-mark"><span>H</span><i></i><span>R</span></span><span class="brand-copy">Health Research Database<small>Healthspan Habits Test</small></span></a><nav><a href="/">Research database</a><a class="nav-cta" href="/healthspan/?challenge={score}">Beat this score</a></nav></div></header>
<main class="score-landing"><div class="wrap score-landing-grid"><section class="shared-score-card"><div class="shared-score-label">Healthspan Habits Score</div><div class="shared-score-number">{score}<span>/ 100</span></div><h1>{b}</h1><p>This score came from the same transparent 10-question habits test you're about to take.</p><div class="shared-score-footer">HealthResearchDatabase.com</div></section><section class="score-landing-copy"><div class="eyebrow">You've been challenged</div><h2>Think you can score higher than {score}?</h2><p>Answer the exact same questions. No login, no email gate, and no hidden scoring model.</p><a class="button button-light button-large" href="/healthspan/?challenge={score}">Take the challenge →</a><p class="score-fineprint">Educational habit-alignment index only. Not a biological-age test, diagnosis, medical risk score or lifespan prediction.</p></section></div></main></body></html>'''

for s in range(101):
    d=SCORES/str(s);d.mkdir(exist_ok=True);(d/'index.html').write_text(page(s),encoding='utf-8')
    make_score_img(s,SCORE_IMG/f'score-{s}.png')

# General Open Graph cards
for filename,title,subtitle in [
    ('og-home.png','What does the research actually say?','Search the evidence. Test your habits. Challenge a friend.'),
    ('og-healthspan.png','How healthy are your daily habits?','Ten questions. A transparent 0–100 score. Challenge a friend.')]:
    im=Image.new('RGB',(1200,630),'#f3f0e7');d=ImageDraw.Draw(im)
    d.rectangle((0,0,25,630),fill='#0c716b');d.text((72,62),'HEALTH RESEARCH DATABASE',font=font(20,True),fill='#0c716b')
    words=title.split();lines=[];line=''
    for word in words:
        test=(line+' '+word).strip()
        if d.textbbox((0,0),test,font=font(62,serif=True))[2]>980 and line:
            lines.append(line);line=word
        else:line=test
    if line:lines.append(line)
    y=150
    for line in lines:
        d.text((72,y),line,font=font(62,serif=True),fill='#102128');y+=76
    d.text((72,y+25),subtitle,font=font(27),fill='#647177')
    d.line((72,548,1128,548),fill='#cbc5b7',width=2);d.text((72,570),'HealthResearchDatabase.com',font=font(18,True),fill='#647177')
    im.save(ASSETS/filename,optimize=True)
print('Generated score pages and social images')
