#!/bin/bash

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "AWS CLI is not installed. Please install it first."
    exit 1
fi

# Function to process a single world
process_world() {
    local WORLD_ID=$1
    echo "===== Processing world: ${WORLD_ID} ====="

    # Define directories
    BASE_DIR="images/${WORLD_ID}"
    OUTPUT_DIR="outputs/${WORLD_ID}"
    GIF_DIR="gifs/${WORLD_ID}"

    # Create required directories
    mkdir -p ${BASE_DIR}/players
    mkdir -p ${BASE_DIR}/tribes/zoc
    mkdir -p ${BASE_DIR}/tribes/no_zoc
    mkdir -p ${OUTPUT_DIR}
    mkdir -p ${GIF_DIR}

    # Count files to be downloaded
    echo "Counting files to be downloaded from S3..."
    PLAYER_FILE_COUNT=$(aws s3 ls s3://tw-timelapse/${WORLD_ID}/top_players/ --recursive 2>/dev/null | wc -l)
    TRIBE_ZOC_FILE_COUNT=$(aws s3 ls s3://tw-timelapse/${WORLD_ID}/top_tribes_zoc/ --recursive 2>/dev/null | wc -l)
    TRIBE_NO_ZOC_FILE_COUNT=$(aws s3 ls s3://tw-timelapse/${WORLD_ID}/top_tribes_no_zoc/ --recursive 2>/dev/null | wc -l)

    TOTAL_FILES=$((PLAYER_FILE_COUNT + TRIBE_ZOC_FILE_COUNT + TRIBE_NO_ZOC_FILE_COUNT))

    if [ $TOTAL_FILES -eq 0 ]; then
        echo "No files found for world ${WORLD_ID}. Skipping..."
        return 1
    fi

    echo "Found ${PLAYER_FILE_COUNT} player maps, ${TRIBE_ZOC_FILE_COUNT} tribe ZOC maps, and ${TRIBE_NO_ZOC_FILE_COUNT} tribe no-ZOC maps for world ${WORLD_ID}."

    # Clear image folders before syncing
    echo "Clearing image folders..."
    rm -rf ${BASE_DIR}/players/*
    rm -rf ${BASE_DIR}/tribes/zoc/*
    rm -rf ${BASE_DIR}/tribes/no_zoc/*

    # Download player maps
    echo "Downloading player maps..."
    aws s3 sync s3://tw-timelapse/${WORLD_ID}/top_players/ ${BASE_DIR}/players/ --quiet

    # Download tribe maps with zones of control
    echo "Downloading tribe maps with zones of control..."
    aws s3 sync s3://tw-timelapse/${WORLD_ID}/top_tribes_zoc/ ${BASE_DIR}/tribes/zoc/ --quiet

    # Download tribe maps without zones of control
    echo "Downloading tribe maps without zones of control..."
    aws s3 sync s3://tw-timelapse/${WORLD_ID}/top_tribes_no_zoc/ ${BASE_DIR}/tribes/no_zoc/ --quiet

    # Rename files to sequential numbers for ffmpeg
    echo "Preparing files for processing..."
    
    # Players
    if [ -n "$(ls -A ${BASE_DIR}/players/ 2>/dev/null)" ]; then
        pushd ${BASE_DIR}/players/ > /dev/null
        ls -1 *.png 2>/dev/null | sort | awk '{printf "mv \"%s\" \"%d.png\"\n", $0, NR}' | bash
        popd > /dev/null
    else
        echo "No player maps found for ${WORLD_ID}"
    fi
    
    # Tribes with zones of control
    if [ -n "$(ls -A ${BASE_DIR}/tribes/zoc/ 2>/dev/null)" ]; then
        pushd ${BASE_DIR}/tribes/zoc/ > /dev/null
        ls -1 *.png 2>/dev/null | sort | awk '{printf "mv \"%s\" \"%d.png\"\n", $0, NR}' | bash
        popd > /dev/null
    else
        echo "No tribe ZOC maps found for ${WORLD_ID}"
    fi
    
    # Tribes without zones of control
    if [ -n "$(ls -A ${BASE_DIR}/tribes/no_zoc/ 2>/dev/null)" ]; then
        pushd ${BASE_DIR}/tribes/no_zoc/ > /dev/null
        ls -1 *.png 2>/dev/null | sort | awk '{printf "mv \"%s\" \"%d.png\"\n", $0, NR}' | bash
        popd > /dev/null
    else
        echo "No tribe no-ZOC maps found for ${WORLD_ID}"
    fi

    # Process files
    echo "Generating timelapses for world ${WORLD_ID}..."

    # Create timers
    start_time=$(date +%s)

    # Players
    if [ -n "$(ls -A ${BASE_DIR}/players/ 2>/dev/null)" ]; then
        echo "Generating player timelapse..."
        ffmpeg -thread_queue_size 4096 -framerate 5 -i ${BASE_DIR}/players/%d.png -crf 16 -vf "minterpolate='mi_mode=mci:mc_mode=aobmc:vsbmc=1:fps=5',hqdn3d" -pix_fmt yuv420p ${OUTPUT_DIR}/${WORLD_ID}_player_output.mp4 -y -loglevel error

        # Convert MP4 to GIF for players
        ffmpeg -thread_queue_size 4096 -i ${OUTPUT_DIR}/${WORLD_ID}_player_output.mp4 -vf "fps=5,scale=iw/2:-1:flags=lanczos,split[s0][s1];[s0]palettegen=max_colors=256[p];[s1][p]paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle" -y ${GIF_DIR}/${WORLD_ID}_player_output.gif -loglevel error
    fi

    # Tribes with zones of control
    if [ -n "$(ls -A ${BASE_DIR}/tribes/zoc/ 2>/dev/null)" ]; then
        echo "Generating tribe timelapse with zones of control..."
        ffmpeg -thread_queue_size 4096 -framerate 5 -i ${BASE_DIR}/tribes/zoc/%d.png -crf 16 -vf "minterpolate='mi_mode=mci:mc_mode=aobmc:vsbmc=1:fps=5',hqdn3d" -pix_fmt yuv420p ${OUTPUT_DIR}/${WORLD_ID}_tribe_zoc_output.mp4 -y -loglevel error

        # Convert MP4 to GIF for tribes with zones of control
        ffmpeg -thread_queue_size 4096 -i ${OUTPUT_DIR}/${WORLD_ID}_tribe_zoc_output.mp4 -vf "fps=5,scale=iw/2:-1:flags=lanczos,split[s0][s1];[s0]palettegen=max_colors=256[p];[s1][p]paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle" -y ${GIF_DIR}/${WORLD_ID}_tribe_zoc_output.gif -loglevel error
    fi

    # Tribes without zones of control
    if [ -n "$(ls -A ${BASE_DIR}/tribes/no_zoc/ 2>/dev/null)" ]; then
        echo "Generating tribe timelapse without zones of control..."
        ffmpeg -thread_queue_size 4096 -framerate 5 -i ${BASE_DIR}/tribes/no_zoc/%d.png -crf 16 -vf "minterpolate='mi_mode=mci:mc_mode=aobmc:vsbmc=1:fps=5',hqdn3d" -pix_fmt yuv420p ${OUTPUT_DIR}/${WORLD_ID}_tribe_no_zoc_output.mp4 -y -loglevel error

        # Convert MP4 to GIF for tribes without zones of control
        ffmpeg -thread_queue_size 4096 -i ${OUTPUT_DIR}/${WORLD_ID}_tribe_no_zoc_output.mp4 -vf "fps=5,scale=iw/2:-1:flags=lanczos,split[s0][s1];[s0]palettegen=max_colors=256[p];[s1][p]paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle" -y ${GIF_DIR}/${WORLD_ID}_tribe_no_zoc_output.gif -loglevel error
    fi

    # Calculate elapsed time
    end_time=$(date +%s)
    elapsed_time=$((end_time - start_time))

    echo "Completed processing for world ${WORLD_ID}."
    echo "Time taken: ${elapsed_time} seconds"
    echo ""
    
    return 0
}

# Main script starts here
echo "Please select how you want to specify worlds:"
echo "1) Single world (e.g., en144)"
echo "2) Range of worlds (e.g., en142-en146)"
echo "3) List of worlds (e.g., enc1,enc2,en144)"
read -p "Enter your choice (1/2/3): " CHOICE

WORLDS_TO_PROCESS=()

case $CHOICE in
    1)
        read -p "Enter the world ID (e.g., en144): " WORLD_ID
        if [ -z "$WORLD_ID" ]; then
            echo "No world ID provided. Exiting."
            exit 1
        fi
        WORLDS_TO_PROCESS+=("$WORLD_ID")
        ;;
    2)
        read -p "Enter the prefix (e.g., en): " PREFIX
        read -p "Enter the start number: " START_NUM
        read -p "Enter the end number: " END_NUM
        
        if [ -z "$PREFIX" ] || [ -z "$START_NUM" ] || [ -z "$END_NUM" ]; then
            echo "Invalid input. Exiting."
            exit 1
        fi
        
        for ((i=START_NUM; i<=END_NUM; i++)); do
            WORLDS_TO_PROCESS+=("$PREFIX$i")
        done
        ;;
    3)
        read -p "Enter comma-separated list of worlds (e.g., enc1,enc2,en144): " WORLD_LIST
        if [ -z "$WORLD_LIST" ]; then
            echo "No worlds provided. Exiting."
            exit 1
        fi
        
        IFS=',' read -ra WORLD_ARRAY <<< "$WORLD_LIST"
        for WORLD in "${WORLD_ARRAY[@]}"; do
            WORLDS_TO_PROCESS+=("$WORLD")
        done
        ;;
    *)
        echo "Invalid choice. Exiting."
        exit 1
        ;;
esac

echo "Will process the following worlds: ${WORLDS_TO_PROCESS[*]}"
read -p "Do you want to continue? (y/n): " CONFIRM

if [ "$CONFIRM" != "y" ]; then
    echo "Operation cancelled. Exiting."
    exit 0
fi

# Process each world
SUCCESSFUL_WORLDS=()
FAILED_WORLDS=()

for WORLD_ID in "${WORLDS_TO_PROCESS[@]}"; do
    if process_world "$WORLD_ID"; then
        SUCCESSFUL_WORLDS+=("$WORLD_ID")
    else
        FAILED_WORLDS+=("$WORLD_ID")
    fi
done

# Final summary
echo "===== Processing Summary ====="
echo "Successfully processed worlds: ${#SUCCESSFUL_WORLDS[@]}"
if [ ${#SUCCESSFUL_WORLDS[@]} -gt 0 ]; then
    echo "  ${SUCCESSFUL_WORLDS[*]}"
fi

echo "Failed to process worlds: ${#FAILED_WORLDS[@]}"
if [ ${#FAILED_WORLDS[@]} -gt 0 ]; then
    echo "  ${FAILED_WORLDS[*]}"
fi

echo "MP4 files are in the 'outputs/' directory"
echo "GIF files are in the 'gifs/' directory"
