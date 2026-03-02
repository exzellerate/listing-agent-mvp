# Test Images Directory

This directory should contain the test images referenced in `test_data.csv`.

## Required Images

According to `test_data.csv`, the following images are needed:

1. `dyson_vacuum.jpg` - Dyson Ball Multi Floor Vacuum
2. `iphone_13.jpg` - iPhone 13
3. `nike_shoes.jpg` - Nike Air Max Sneakers
4. `macbook_pro.jpg` - MacBook Pro 13-inch
5. `kindle_paperwhite.jpg` - Kindle Paperwhite
6. `instant_pot.jpg` - Instant Pot Duo
7. `fitbit_watch.jpg` - Fitbit Versa 3
8. `ps5_controller.jpg` - PlayStation 5 DualSense Controller
9. `lego_set.jpg` - LEGO Star Wars Millennium Falcon
10. `airpods_pro.jpg` - Apple AirPods Pro

## Image Requirements

- **Format:** JPEG, PNG, WebP, or GIF
- **Size:** Maximum 10MB per image
- **Resolution:** At least 640x480 recommended
- **Quality:** Clear, well-lit product photos work best

## How to Add Images

### Option 1: Download from Online Sources
Find product images online (ensure you have rights to use them) and save them here with the exact filenames listed above.

### Option 2: Copy from Existing Photos
If you have product photos on your computer:
```bash
cp ~/Downloads/your-product-photo.jpg test_images/dyson_vacuum.jpg
```

### Option 3: Use the Dyson Vacuum Photo
If you've already tested with the Dyson vacuum:
```bash
cp ~/Downloads/DysonVaccum.jpg test_images/dyson_vacuum.jpg
```

## Testing with Partial Dataset

You can test with just a few images by:

1. Adding only the images you have
2. Editing `test_data.csv` to comment out (or delete) rows for missing images
3. Running tests with the available images

Example - test with just Dyson vacuum:
```bash
# Copy your image
cp ~/Downloads/DysonVaccum.jpg test_images/dyson_vacuum.jpg

# Edit test_data.csv to keep only the dyson_vacuum row

# Run tests
python test_runner.py --csv test_data.csv --images ./test_images
```

## Verify Images

Check that images are loaded correctly:
```bash
ls -lh test_images/
```

You should see files like:
```
-rw-r--r--  1 user  staff   335K Oct 11 16:00 dyson_vacuum.jpg
-rw-r--r--  1 user  staff   428K Oct 11 16:00 iphone_13.jpg
...
```
