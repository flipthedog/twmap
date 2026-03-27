#!/bin/bash

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "AWS CLI is not installed. Please install it first."
    exit 1
fi

# Function to process a single world for tribes
process_world() {
    local WORLD_ID=$1
    local TARGET_DURATION=$2
    echo "===== Processing world: ${WORLD_ID} ====="

    # Define directories
    BASE_DIR="images/${WORLD_ID}"
    OUTPUT_DIR="outputs/${WORLD_ID}"
    GIF_DIR="gifs/${WORLD_ID}"

    # Create required directories
    mkdir -p ${BASE_DIR}/tribes
    mkdir -p ${OUTPUT_DIR}
    mkdir -p ${GIF_DIR}

    # Count files to be downloaded
    echo "Counting files to be downloaded from S3..."
    TRIBE_FILE_COUNT=$(aws s3 ls s3://tw-timelapse/${WORLD_ID}/top_tribes/ --recursive 2>/dev/null | wc -l)

    if [ $TRIBE_FILE_COUNT -eq 0 ]; then
        echo "No tribe maps found for world ${WORLD_ID}. Skipping..."
        return 1
    fi

    echo "Found ${TRIBE_FILE_COUNT} tribe maps for world ${WORLD_ID}."

    # Clear image folder before syncing
    echo "Clearing image folder..."
    rm -rf ${BASE_DIR}/tribes/*

    # Download tribe maps
    echo "Downloading tribe maps..."
    aws s3 sync s3://tw-timelapse/${WORLD_ID}/top_tribes/ ${BASE_DIR}/tribes/ --quiet

    # Rename files to sequential numbers for ffmpeg
    echo "Preparing files for processing..."
    
    if [ -n "$(ls -A ${BASE_DIR}/tribes/ 2>/dev/null)" ]; then
        pushd ${BASE_DIR}/tribes/ > /dev/null
        ls -1 *.png 2>/dev/null | sort | awk '{printf "mv \"%s\" \"%d.png\"\n", $0, NR}' | bash
        popd > /dev/null
    else
        echo "No tribe maps found for ${WORLD_ID}"
        return 1
    fi

    # Function to calculate framerate for target duration video
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
    echo "Generating tribe timelapse for world ${WORLD_ID}..."
    echo "Target video duration: ${TARGET_DURATION} seconds"

    # Create timers
    start_time=$(date +%s)

    TRIBE_COUNT=$(ls -1 ${BASE_DIR}/tribes/*.png 2>/dev/null | wc -l)
    TRIBE_FRAMERATE=$(calculate_framerate $TRIBE_COUNT)
    
    echo "Generating tribe timelapse (using Apple GPU acceleration)..."
    echo "  - Images: ${TRIBE_COUNT}"
    echo "  - Calculated framerate: ${TRIBE_FRAMERATE} fps"
    echo "  - Estimated duration: $(echo "scale=1; $TRIBE_COUNT / $TRIBE_FRAMERATE" | bc -l) seconds"
    echo ""
    
    # Crisp and sharp (no interpolation, best for timelapses)
    ffmpeg -thread_queue_size 4096 \
     -framerate ${TRIBE_FRAMERATE} \
     -i ${BASE_DIR}/tribes/%d.png \
     -c:v h264_videotoolbox \
     -b:v 12M \
     -allow_sw 1 \
     -movflags +faststart \
     -vf "hqdn3d=1:0.8:2:1.5,unsharp=5:5:1.0:5:5:0.0" \
     -pix_fmt yuv420p ${OUTPUT_DIR}/${WORLD_ID}_tribe_output.mp4 \
     -y -loglevel error
    
    if [ $? -eq 0 ]; then
        echo "✓ Timelapse created successfully"
        
        # Copy final image from source files
        echo "Saving final image..."
        FINAL_IMAGE=$(ls -1 ${BASE_DIR}/tribes/*.png | tail -1)
        if [ -n "$FINAL_IMAGE" ]; then
            cp "$FINAL_IMAGE" ${OUTPUT_DIR}/${WORLD_ID}_tribe_final_frame.png
            if [ $? -eq 0 ]; then
                echo "✓ Final image saved"
            fi
        fi
    else
        echo "✗ Failed to create timelapse"
        return 1
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
echo "===== Tribe Timelapse Generator ====="
echo ""

# Ask for target video duration
read -p "Enter the target video duration in seconds (e.g., 60, 180): " TARGET_DURATION
if [ -z "$TARGET_DURATION" ] || ! [[ "$TARGET_DURATION" =~ ^[0-9]+$ ]]; then
    echo "Invalid duration. Using default of 180 seconds (3 minutes)."
    TARGET_DURATION=180
fi

echo ""
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
echo "Target duration: ${TARGET_DURATION} seconds"
read -p "Do you want to continue? (y/n): " CONFIRM

if [ "$CONFIRM" != "y" ]; then
    echo "Operation cancelled. Exiting."
    exit 0
fi

# Process each world
SUCCESSFUL_WORLDS=()
FAILED_WORLDS=()

for WORLD_ID in "${WORLDS_TO_PROCESS[@]}"; do
    if process_world "$WORLD_ID" "$TARGET_DURATION"; then
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

echo "Tribe MP4 files are in the 'outputs/' directory"
