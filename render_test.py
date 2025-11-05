from dashboard_renderer import render_dashboard_image

# Create sample reminders
sample = [
    {'id': 101, 'message': 'Check the oven', 'time_display': 'Nov 04, 10:15 AM'},
    {'id': 102, 'message': 'Team meeting', 'time_display': 'Nov 04, 03:00 PM'},
    {'id': 103, 'message': 'Pay bills', 'time_display': 'Nov 06, 09:00 AM'},
]

img_io = render_dashboard_image(sample, 'TestUser')
with open('dashboard_test.png', 'wb') as f:
    f.write(img_io.read())

print('Wrote dashboard_test.png')
