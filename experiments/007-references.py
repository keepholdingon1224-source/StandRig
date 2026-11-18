"""Record the reference poses and connection crops for this fixed-head PNG study."""
from pathlib import Path
import json
from PIL import Image, ImageDraw

src = Image.open('source_007/original.png')
out = Path('results/007-character-application/rigging/references')
out.mkdir(parents=True, exist_ok=True)
groups = {
    'face': [(480, 110, 735, 425, 'Neutral face; yaw/pitch/roll fixed')],
    'body': [(175, 100, 971, 1970, 'Neutral body; yaw/pitch/roll fixed')],
    'connections': [(390, 407, 710, 570, 'Hair roots / upper hair'),
                    (500, 285, 676, 475, 'Jaw / neck'),
                    (440, 390, 730, 510, 'Collar / shoulders'),
                    (352, 608, 828, 866, 'Sleeves / arms'),
                    (401, 708, 737, 925, 'Waist / skirt / upper leg coverage'),
                    (404, 1550, 760, 1960, 'Hem / lower legs')]
}
for name, panels in groups.items():
    canvas = Image.new('RGB', (640, 340*((len(panels)+1)//2)), '#f4f4f4')
    draw = ImageDraw.Draw(canvas)
    for i, (*box, title) in enumerate(panels):
        panel = src.crop(box)
        panel.thumbnail((310,310))
        x, y = i%2*320, i//2*340
        canvas.paste(panel,(x+(320-panel.width)//2,y+24))
        draw.text((x+6,y+5),title,fill='black')
    canvas.save(out/f'{name}.png')
(out/'manifest.json').write_text(json.dumps({
    'sourceRevision':'13dc02a48f9ace0e2c657dbb751fd7ae865a9138',
    'sourceSHA256':'a1388c37f35c19278d346ab4491c8bcc919e1f375b07f312a70ab7e87bbcbcea',
    'panelOrderAndCropXYXY':groups,
    'poseExtremes':{'headYawPitchRoll':[0,0,0],'bodyYawPitchRoll':[0,0,0]},
    'prompts':None,'method':'Unmodified source crops; only secondary motion is in scope',
    'acceptanceChecks':['Hair roots and waist stay attached','Visible face and fixed body pixels are preserved',
                        'Hem ornament and continuous skirt center remain intact','Review revealed artwork for seams']
},indent=2)+'\n')
