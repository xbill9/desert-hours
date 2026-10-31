#!/usr/bin/env python3
"""Record the captioned demo from the live site with the system Chrome."""
import pathlib, sys
from playwright.sync_api import sync_playwright
URL = "https://d35zkoavyfqlat.cloudfront.net/"
OUT = pathlib.Path(__file__).resolve().parent.parent / "media"
CAP = """(()=>{const d=document.createElement('div');d.id='cap';d.style.cssText='position:fixed;left:38%;transform:translateX(-50%);top:24px;max-width:700px;background:#000d;color:#fff;font:600 22px/1.35 system-ui;padding:12px 20px;border-radius:10px;z-index:9999;text-align:center';document.body.append(d)})()"""
def cap(p, t): p.evaluate("t=>{document.getElementById('cap').textContent=t}", t)
def hour(p, h): p.evaluate("h=>{const e=document.getElementById('hour');e.value=h;e.dispatchEvent(new Event('input'))}", h)
with sync_playwright() as w:
    b = w.chromium.launch(channel="chrome", headless=True, args=["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"])
    errs = []
    if "--shots" in sys.argv:
        for name, vp in (("desktop", (1408, 900)), ("phone", (390, 844))):
            p = b.new_page(viewport=dict(width=vp[0], height=vp[1]))
            p.on("pageerror", lambda e: errs.append(str(e)))
            p.goto(URL); p.wait_for_timeout(7000)
            print(name, "scrollWidth", p.evaluate("document.documentElement.scrollWidth"), vp[0])
            hour(p, 8); p.wait_for_timeout(1500); p.screenshot(path=OUT / f"{name}-8am.png")
            hour(p, 27); p.wait_for_timeout(1500); p.screenshot(path=OUT / f"{name}-3am.png")
            p.close()
        print("errors", errs); b.close(); sys.exit()
    c = b.new_context(viewport=dict(width=1280, height=720), record_video_dir=str(OUT / "raw"), record_video_size=dict(width=1280, height=720))
    p = c.new_page(); p.goto(URL); p.wait_for_timeout(7000); p.evaluate(CAP)
    p.add_style_tag(content=".top{display:none}.app{grid-template-rows:440px auto;padding-top:10px}")
    p.evaluate("window.dispatchEvent(new Event('resize'))"); p.wait_for_timeout(1000)
    cap(p, "A transit desert can open and close in a single day."); p.wait_for_timeout(5000)
    cap(p, "Mercer County, NJ. 16,114 households have no car."); p.wait_for_timeout(5000)
    cap(p, "Blue is a 10-minute walk to running service, measured on real streets."); p.wait_for_timeout(5500)
    cap(p, "At 8 AM, 6,388 car-free households are out of reach."); p.wait_for_timeout(5000)
    cap(p, "Watch the day pass.")
    for h in range(8, 29):
        hour(p, h); p.wait_for_timeout(1150)
    cap(p, "By 3 AM, it is 14,095."); hour(p, 27); p.wait_for_timeout(5500)
    hour(p, 8); cap(p, "Now one place: Trenton Tract 1. About 445 households have no car."); p.evaluate("document.getElementById('story').click()"); p.wait_for_timeout(1000); hour(p, 8); p.wait_for_timeout(6500)
    cap(p, "At 8 AM, 73% of its housing is within a 10-minute walk of service."); p.wait_for_timeout(5500)
    hour(p, 23); cap(p, "At 11 PM, none of it is."); p.wait_for_timeout(5000)
    cap(p, "The hospital is an 11-minute drive. Leave by transit at 2 AM and it takes 3 hours 29 minutes."); p.wait_for_timeout(8000)
    p.evaluate("document.getElementById('cap').style.display='none'"); p.evaluate("document.querySelector('.clock').scrollIntoView()"); p.wait_for_timeout(500); p.evaluate("document.getElementById('cap').style.display='block'")
    p.evaluate("scrollTo(0,0)")
    cap(p, "Built with Amazon Location Service, S3 and CloudFront. Scheduled service only."); p.wait_for_timeout(5500)
    cap(p, "Click any tract. Move the clock. See who gets left behind, and when."); p.wait_for_timeout(5000)
    p.close(); c.close(); b.close()
