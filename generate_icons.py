#!/usr/bin/env python3
"""
Generate PWA icons for Voicebot AI
Creates icons in various sizes with a beautiful gradient background and robot emoji
"""

import os
from pathlib import Path

# Create icons directory
icons_dir = Path('static/icons')
icons_dir.mkdir(parents=True, exist_ok=True)

# Icon sizes needed for PWA
ICON_SIZES = [72, 96, 128, 144, 152, 192, 384, 512]

# SVG template with gradient background and robot emoji
SVG_TEMPLATE = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" width="{size}" height="{size}">
  <defs>
    <linearGradient id="grad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#667eea;stop-opacity:1" />
      <stop offset="50%" style="stop-color:#764ba2;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#f093fb;stop-opacity:1" />
    </linearGradient>
    <filter id="shadow">
      <feDropShadow dx="0" dy="2" stdDeviation="4" flood-opacity="0.3"/>
    </filter>
  </defs>

  <!-- Background -->
  <rect width="{size}" height="{size}" fill="url(#grad)" rx="{radius}"/>

  <!-- Robot emoji as text -->
  <text
    x="50%"
    y="50%"
    font-size="{emoji_size}"
    text-anchor="middle"
    dominant-baseline="central"
    filter="url(#shadow)"
  >🤖</text>
</svg>'''

print('🎨 Generating PWA icons for Voicebot AI...\n')

for size in ICON_SIZES:
    # Calculate emoji size and border radius
    emoji_size = int(size * 0.6)
    radius = int(size * 0.15)

    # Generate SVG
    svg_content = SVG_TEMPLATE.format(
        size=size,
        emoji_size=emoji_size,
        radius=radius
    )

    # Save SVG file (can be converted to PNG later if needed)
    filename = f'icon-{size}x{size}.svg'
    filepath = icons_dir / filename

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(svg_content)

    print(f'✅ Created {filename}')

# Generate PNG version info
print('\n📝 SVG icons created successfully!')
print('\n💡 To convert to PNG (optional):')
print('   Install: brew install librsvg (Mac) or apt-get install librsvg2-bin (Linux)')
print('   Then run: for f in static/icons/*.svg; do rsvg-convert -h $(basename $f .svg | grep -o "[0-9]*") $f > ${f%.svg}.png; done')

# Create shortcut icons
print('\n🔗 Creating shortcut icons...')

SHORTCUT_SVG = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 96 96" width="96" height="96">
  <defs>
    <linearGradient id="grad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#667eea;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#764ba2;stop-opacity:1" />
    </linearGradient>
  </defs>

  <rect width="96" height="96" fill="url(#grad)" rx="14"/>
  <text x="50%" y="50%" font-size="50" text-anchor="middle" dominant-baseline="central">{emoji}</text>
</svg>'''

shortcuts = [
    ('shortcut-new-chat.svg', '💬'),
    ('shortcut-calendar.svg', '📅')
]

for filename, emoji in shortcuts:
    filepath = icons_dir / filename
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(SHORTCUT_SVG.format(emoji=emoji))
    print(f'✅ Created {filename}')

# Create badge icon for notifications
BADGE_SVG = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 72 72" width="72" height="72">
  <circle cx="36" cy="36" r="36" fill="#667eea"/>
  <text x="50%" y="50%" font-size="40" text-anchor="middle" dominant-baseline="central">🤖</text>
</svg>'''

badge_path = icons_dir / 'badge-72x72.svg'
with open(badge_path, 'w', encoding='utf-8') as f:
    f.write(BADGE_SVG)
print(f'✅ Created badge-72x72.svg')

# Create Apple touch icon (180x180 is standard)
apple_svg = SVG_TEMPLATE.format(size=180, emoji_size=108, radius=0)
apple_path = icons_dir / 'apple-touch-icon.svg'
with open(apple_path, 'w', encoding='utf-8') as f:
    f.write(apple_svg)
print(f'✅ Created apple-touch-icon.svg')

print('\n✨ All PWA icons generated successfully!')
print(f'📁 Location: {icons_dir.absolute()}')
