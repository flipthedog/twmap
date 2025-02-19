#!/bin/bash

if [ -z "$1" ]; then
    echo "No directory name provided. Defaulting to 'images/'."
    DIR="images/"
else
    DIR=$1
fi

# Generate list of top-level directories
directories=$(find $DIR -mindepth 1 -maxdepth 1 -type d)

echo "Found the following top-level directories:"
echo "$directories"

read -p "Generate timelapses for all top-level directories? (y/n): " generate_all

if [ "$generate_all" == "y" ]; then
    for dir in $directories; do
        start_time=$(date +%s)
        echo "Generating timelapse for $dir"
        
        output_dir="outputs/$(basename $dir)"
        mkdir -p $output_dir

        # Players
        # ffmpeg -framerate 5 -i $dir/players/%d.png -crf 16 -vf "minterpolate='mi_mode=mci:mc_mode=aobmc:vsbmc=1:fps=5',hqdn3d" -pix_fmt yuv420p $output_dir/player_output.mp4 -y

        palette_file="palette_$(basename $dir).png"
        ffmpeg -thread_queue_size 1024 -framerate 5 -i images/en144/players/%d.png -vf "palettegen=max_colors=32" -update 1 $palette_file -y   
        ffmpeg -thread_queue_size 1024 -framerate 5 -i $dir/players/%d.png -i $palette_file -lavfi "paletteuse" $output_dir/player_output.gif -y

        # # Tribes with zones of control
        # ffmpeg -framerate 5 -i $dir/tribes/zoc/%d.png -crf 16 -vf "minterpolate='mi_mode=mci:mc_mode=aobmc:vsbmc=1:fps=5',hqdn3d" -pix_fmt yuv420p $output_dir/tribe_zoc_output.mp4 -y

        # ffmpeg -framerate 5 -i $dir/tribes/zoc/%d.png -vf "palettegen" palette.png -y
        # ffmpeg -framerate 5 -i $dir/tribes/zoc/%d.png -i palette.png -lavfi "paletteuse" -fps_mode vfr $output_dir/tribe_zoc_output.gif -y

        # # Tribes without zones of control
        # ffmpeg -framerate 5 -i $dir/tribes/no_zoc/%d.png -crf 16 -vf "minterpolate='mi_mode=mci:mc_mode=aobmc:vsbmc=1:fps=5',hqdn3d" -pix_fmt yuv420p $output_dir/tribe_no_zoc_output.mp4 -y

        # ffmpeg -framerate 5 -i $dir/tribes/no_zoc/%d.png -vf "palettegen" palette.png -y
        # ffmpeg -framerate 5 -i $dir/tribes/no_zoc/%d.png -i palette.png -lavfi "paletteuse" -fps_mode vfr $output_dir/tribe_no_zoc_output.gif -y

        end_time=$(date +%s)
        elapsed_time=$((end_time - start_time))
        echo "Time taken for $dir: $elapsed_time seconds"
    done
else
    echo "No timelapses generated."
fi

# ffmpeg -framerate 5 -i images/$DIR/custom_tribes/no_zoc/%d.png -vf "palettegen" palette.png -y
# ffmpeg -framerate 5 -i images/$DIR/custom_tribes/no_zoc/%d.png -i palette.png -lavfi "paletteuse" images/${DIR}_tribe_no_zoc_output.gif -y

# # Tribes with zones of control
# ffmpeg -framerate 5 -i images/$DIR/custom_tribes/zoc/%d.png -crf 16 -vf "minterpolate='mi_mode=mci:mc_mode=aobmc:vsbmc=1:fps=5',hqdn3d" -pix_fmt yuv420p images/${DIR}_tribe_zoc_output.mp4 -y

# ffmpeg -framerate 5 -i images/$DIR/custom_tribes/zoc/%d.png -vf "palettegen" palette.png -y
# ffmpeg -framerate 5 -i images/$DIR/custom_tribes/zoc/%d.png -i palette.png -lavfi "paletteuse" images/${DIR}_tribe_zoc_output.gif -y

# # Compressed GIF for tribes with zones of control
# ffmpeg -framerate 5 -i images/$DIR/custom_tribes/zoc/%d.png -filter_complex "[0:v] fps=3,scale=-1:1000,mpdecimate,split [a][b];[a] palettegen=max_colors=254 [p];[b][p] paletteuse=dither=bayer:bayer_scale=5" images/${DIR}_tribe_zoc_compressed.gif -y