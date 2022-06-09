from PIL import Image, ImageDraw, ImageFont, ImageOps

img = Image.new('RGB', (1000, 1000), (32, 32, 32))
drw = ImageDraw.Draw(img)
fnt_sml = ImageFont.truetype('./Roboto-Regular.ttf', 34)
fnt_med = ImageFont.truetype('./Roboto-Regular.ttf', 40)
fnt_lrg = ImageFont.truetype('./Roboto-Regular.ttf', 80)
txt_clr = (255, 255, 255)
drw.text((40, 40), "dailyrun.app", fill=txt_clr, font=fnt_med)

profile_img = Image.open('original.jpg')
profile_img.thumbnail((500,500))
img.paste(profile_img, (250, 125))

name_txt = "Luke Weiler"
name_width, _ = drw.textsize(name_txt, font=fnt_lrg)
drw.text(((1000-name_width)/2, 650), name_txt, fill=txt_clr, font=fnt_lrg)

streak_lbl_txt = "Has a streak of:"
streak_lbl_width, _ = drw.textsize(streak_lbl_txt, font=fnt_sml)
drw.text(((1000-streak_lbl_width)/2, 750), streak_lbl_txt, fill=txt_clr, font=fnt_sml)

streak_txt = "30 days"
streak_width, _ = drw.textsize(streak_txt, font=fnt_lrg)
drw.text(((1000-streak_width)/2, 800), streak_txt, fill=txt_clr, font=fnt_lrg)

drw.text((40, 920), "Started May 09, 2022", fill=txt_clr, font=fnt_med)

powered_by_image = Image.open('api_logo_pwrdBy_strava_horiz_gray.png')
img.paste(powered_by_image, (650, 920), powered_by_image)


img.show()
