#!/bin/bash

if [ -z "$1" ]; then
    echo "Usage: $0 <directory_name>"
    exit 1
fi

DIR=$1

# Players
ffmpeg -framerate 5 -i images/$DIR/players/%d.png -crf 16 -vf "minterpolate='mi_mode=mci:mc_mode=aobmc:vsbmc=1:fps=5',hqdn3d" -pix_fmt yuv420p images/${DIR}_player_output.mp4

ffmpeg -framerate 5 -i images/$DIR/players/%d.png -vf "palettegen" palette.png -y   
ffmpeg -framerate 5 -i images/$DIR/players/%d.png -i palette.png -lavfi "paletteuse" images/${DIR}_player_output.gif

# Tribes
ffmpeg -framerate 5 -i images/$DIR/tribes/%d.png -crf 16 -vf "minterpolate='mi_mode=mci:mc_mode=aobmc:vsbmc=1:fps=5',hqdn3d" -pix_fmt yuv420p images/${DIR}_tribe_output.mp4

ffmpeg -framerate 5 -i images/$DIR/tribes/%d.png -vf "palettegen" palette.png -y
ffmpeg -framerate 5 -i images/$DIR/tribes/%d.png -i palette.png -lavfi "paletteuse" images/${DIR}_tribe_output.gif

# Tribes no zones of control
ffmpeg -framerate 5 -i images/$DIR/tribes/no_zoc/%d.png -crf 16 -vf "minterpolate='mi_mode=mci:mc_mode=aobmc:vsbmc=1:fps=5',hqdn3d" -pix_fmt yuv420p images/${DIR}_tribe_no_zoc_output.mp4

ffmpeg -framerate 5 -i images/$DIR/custom_tribes/no_zoc/%d.png -vf "palettegen" palette.png -y
ffmpeg -framerate 5 -i images/$DIR/custom_tribes/no_zoc/%d.png -i palette.png -lavfi "paletteuse" images/${DIR}_tribe_no_zoc_output.gif -y

# Tribes with zones of control
ffmpeg -framerate 5 -i images/$DIR/custom_tribes/zoc/%d.png -crf 16 -vf "minterpolate='mi_mode=mci:mc_mode=aobmc:vsbmc=1:fps=5',hqdn3d" -pix_fmt yuv420p images/${DIR}_tribe_zoc_output.mp4

ffmpeg -framerate 5 -i images/$DIR/custom_tribes/zoc/%d.png -vf "palettegen" palette.png -y
ffmpeg -framerate 5 -i images/$DIR/custom_tribes/zoc/%d.png -i palette.png -lavfi "paletteuse" images/${DIR}_tribe_zoc_output.gif -y

# Compressed GIF for tribes with zones of control
ffmpeg -framerate 5 -i images/$DIR/custom_tribes/zoc/%d.png -filter_complex "[0:v] fps=3,scale=-1:1000,mpdecimate,split [a][b];[a] palettegen=max_colors=254 [p];[b][p] paletteuse=dither=bayer:bayer_scale=5" images/${DIR}_tribe_zoc_compressed.gif -y