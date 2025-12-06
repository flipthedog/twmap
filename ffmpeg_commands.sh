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
    mkdir -p ${BASE_DIR}/tribes
    mkdir -p ${OUTPUT_DIR}
    mkdir -p ${GIF_DIR}

    # Count files to be downloaded
    echo "Counting files to be downloaded from S3..."
    PLAYER_FILE_COUNT=$(aws s3 ls s3://tw-timelapse/${WORLD_ID}/top_players/ --recursive 2>/dev/null | wc -l)
    TRIBE_FILE_COUNT=$(aws s3 ls s3://tw-timelapse/${WORLD_ID}/top_tribes/ --recursive 2>/dev/null | wc -l)

    TOTAL_FILES=$((PLAYER_FILE_COUNT + TRIBE_FILE_COUNT))

    if [ $TOTAL_FILES -eq 0 ]; then
        echo "No files found for world ${WORLD_ID}. Skipping..."
        return 1
    fi

    echo "Found ${PLAYER_FILE_COUNT} player maps and ${TRIBE_FILE_COUNT} tribe maps for world ${WORLD_ID}."

    # Clear image folders before syncing
    echo "Clearing image folders..."
    rm -rf ${BASE_DIR}/players/*
    rm -rf ${BASE_DIR}/tribes/*

    # Download player maps
    echo "Downloading player maps..."
    aws s3 sync s3://tw-timelapse/${WORLD_ID}/top_players/ ${BASE_DIR}/players/ --quiet

    # Download tribe maps
    echo "Downloading tribe maps..."
    aws s3 sync s3://tw-timelapse/${WORLD_ID}/top_tribes/ ${BASE_DIR}/tribes/ --quiet

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
    
    # Tribes
    if [ -n "$(ls -A ${BASE_DIR}/tribes/ 2>/dev/null)" ]; then
        pushd ${BASE_DIR}/tribes/ > /dev/null
        ls -1 *.png 2>/dev/null | sort | awk '{printf "mv \"%s\" \"%d.png\"\n", $0, NR}' | bash
        popd > /dev/null
    else
        echo "No tribe maps found for ${WORLD_ID}"
    fi

    # Calculate optimal framerate for 1-minute video
    TARGET_DURATION=60  # Target video length in seconds
    
    # Function to calculate framerate for 1-minute video
    calculate_framerate() {
        local image_count=$1
        if [ $image_count -gt 0 ]; then
            # Calculate framerate: total_frames / target_duration
            local framerate=$(echo "scale=2; $image_count / $TARGET_DURATION" | bc -l)
            # Ensure minimum framerate of 1 and maximum of 30 for practical purposes
            if (( $(echo "$framerate < 1" | bc -l) )); then
                framerate=1
            elif (( $(echo "$framerate > 30" | bc -l) )); then
                framerate=30
            fi
            echo $framerate
        else
            echo 5  # Default fallback
        fi
    }
    
    # Process files
    echo "Generating timelapses for world ${WORLD_ID}..."
    echo "Target video duration: ${TARGET_DURATION} seconds (1 minute)"

    # Create timers
    start_time=$(date +%s)

    # Players
    if [ -n "$(ls -A ${BASE_DIR}/players/ 2>/dev/null)" ]; then
        PLAYER_COUNT=$(ls -1 ${BASE_DIR}/players/*.png 2>/dev/null | wc -l)
        PLAYER_FRAMERATE=$(calculate_framerate $PLAYER_COUNT)
        
        echo "Generating player timelapse (using Apple GPU acceleration)..."
        echo "  - Images: ${PLAYER_COUNT}"
        echo "  - Calculated framerate: ${PLAYER_FRAMERATE} fps"
        echo "  - Estimated duration: $(echo "scale=1; $PLAYER_COUNT / $PLAYER_FRAMERATE" | bc -l) seconds"

        ffmpeg -thread_queue_size 4096 \
         -framerate ${PLAYER_FRAMERATE} \
         -i ${BASE_DIR}/players/%d.png \
         -c:v h264_videotoolbox \
         -allow_sw 1 \
         -b:v 8M \
         -vf "minterpolate='mi_mode=mci:mc_mode=aobmc:vsbmc=1:fps=${PLAYER_FRAMERATE}',hqdn3d" \
         -pix_fmt yuv420p ${OUTPUT_DIR}/${WORLD_ID}_player_output.mp4 \
         -y -loglevel error

        # Convert MP4 to GIF for players (use lower framerate for smaller GIF)
        # GIF_FRAMERATE=$(echo "scale=0; $PLAYER_FRAMERATE / 2" | bc -l)
        # if [ "$GIF_FRAMERATE" -lt "1" ]; then
        #     GIF_FRAMERATE=1
        # fi
        # ffmpeg -thread_queue_size 1024 -i ${OUTPUT_DIR}/${WORLD_ID}_player_output.mp4 -vf "fps=${GIF_FRAMERATE},scale=iw/2:-1:flags=lanczos,split[s0][s1];[s0]palettegen=max_colors=256[p];[s1][p]paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle" -y ${GIF_DIR}/${WORLD_ID}_player_output.gif -loglevel error
    fi

    # Tribes
    if [ -n "$(ls -A ${BASE_DIR}/tribes/ 2>/dev/null)" ]; then
        TRIBE_COUNT=$(ls -1 ${BASE_DIR}/tribes/*.png 2>/dev/null | wc -l)
        TRIBE_FRAMERATE=$(calculate_framerate $TRIBE_COUNT)
        
        echo "Generating tribe timelapse (using Apple GPU acceleration)..."
        echo "  - Images: ${TRIBE_COUNT}"
        echo "  - Calculated framerate: ${TRIBE_FRAMERATE} fps"
        echo "  - Estimated duration: $(echo "scale=1; $TRIBE_COUNT / $TRIBE_FRAMERATE" | bc -l) seconds"
        
        ffmpeg -thread_queue_size 4096 \
         -framerate ${TRIBE_FRAMERATE} \
         -i ${BASE_DIR}/tribes/%d.png \
         -c:v h264_videotoolbox \
         -b:v 8M \
         -allow_sw 1 \
         -movflags +faststart \
         -vf "minterpolate='mi_mode=mci:mc_mode=aobmc:vsbmc=1:fps=${TRIBE_FRAMERATE}',hqdn3d" \
         -pix_fmt yuv420p ${OUTPUT_DIR}/${WORLD_ID}_tribe_output.mp4 \
         -y -loglevel error

        # Convert MP4 to GIF for tribes (use lower framerate for smaller GIF)
        # GIF_FRAMERATE=$(echo "scale=0; $TRIBE_FRAMERATE / 2" | bc -l)
        # if [ "$GIF_FRAMERATE" -lt "1" ]; then
        #     GIF_FRAMERATE=1
        # fi
        # ffmpeg -thread_queue_size 4096 -i ${OUTPUT_DIR}/${WORLD_ID}_tribe_output.mp4 -vf "fps=${GIF_FRAMERATE},scale=iw/2:-1:flags=lanczos,split[s0][s1];[s0]palettegen=max_colors=256[p];[s1][p]paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle" -y ${GIF_DIR}/${WORLD_ID}_tribe_output.gif -loglevel error
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
