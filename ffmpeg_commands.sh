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

        base_name=$(basename $dir)

        # Players
        ffmpeg -thread_queue_size 1024 -framerate 5 -i $dir/players/%d.png -crf 16 -vf "minterpolate='mi_mode=mci:mc_mode=aobmc:vsbmc=1:fps=5',hqdn3d" -pix_fmt yuv420p $output_dir/${base_name}_player_output.mp4 -y 

        # based on the generated mp4 create a gif with better quality
        ffmpeg -thread_queue_size 1024 -i $output_dir/${base_name}_player_output.mp4 -vf "fps=5,scale=iw/2:-1:flags=lanczos,palettegen" -y $output_dir/palette.png
        ffmpeg -thread_queue_size 1024 -i $output_dir/${base_name}_player_output.mp4 -i $output_dir/palette.png -lavfi "fps=5,scale=iw/2:-1:flags=lanczos,paletteuse" -y $output_dir/${base_name}_player_output.gif

        # Tribes with zones of control
        ffmpeg -thread_queue_size 1024 -framerate 5 -i $dir/tribes/zoc/%d.png -crf 16 -vf "minterpolate='mi_mode=mci:mc_mode=aobmc:vsbmc=1:fps=5',hqdn3d" -pix_fmt yuv420p $output_dir/${base_name}_tribe_zoc_output.mp4 -y

        # based on the generated mp4 create a gif with better quality
        ffmpeg -thread_queue_size 1024 -i $output_dir/${base_name}_tribe_zoc_output.mp4 -vf "fps=5,scale=iw/2:-1:flags=lanczos,palettegen" -y $output_dir/palette.png
        ffmpeg -thread_queue_size 1024 -i $output_dir/${base_name}_tribe_zoc_output.mp4 -i $output_dir/palette.png -lavfi "fps=5,scale=iw/2:-1:flags=lanczos,paletteuse" -y $output_dir/${base_name}_tribe_zoc_output.gif

        # remove pallette.png
        rm $output_dir/palette.png
        
        end_time=$(date +%s)
        elapsed_time=$((end_time - start_time))
        echo "Time taken for $dir: $elapsed_time seconds"
    done
else
    echo "No timelapses generated."
fi
z