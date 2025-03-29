#!/bin/bash

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "AWS CLI is not installed. Please install it first."
    exit 1
fi

# Function to get available worlds from S3
get_available_worlds() {
    echo "Getting list of available worlds from S3..."
    # List all prefixes (folders) at the top level of the bucket
    worlds=$(aws s3 ls s3://tw-timelapse/ | grep PRE | awk '{print $2}' | sed 's/\///g')
    echo "Found worlds: $worlds"
    return 0
}

# Function to get date from one week ago
get_one_week_ago() {
    # Calculate date from one week ago in YYYYMMDD format
    if [ "$(uname)" == "Darwin" ]; then
        # macOS
        date -v-7d +%Y%m%d
    else
        # Linux
        date -d "7 days ago" +%Y%m%d
    fi
}

# Function to process a single world
process_world() {
    local WORLD_ID=$1
    local ONE_WEEK_AGO=$2
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

    # Clear image folders before syncing
    echo "Clearing image folders..."
    rm -rf ${BASE_DIR}/players/*
    rm -rf ${BASE_DIR}/tribes/zoc/*
    rm -rf ${BASE_DIR}/tribes/no_zoc/*

    # List all files and filter by date (past week)
    echo "Listing files from the past week..."
    aws s3 ls s3://tw-timelapse/${WORLD_ID}/top_players/ --recursive | grep -E "[0-9]{8}_[0-9]{6}" | while read -r line; do
        file_path=$(echo "$line" | awk '{print $4}')
        file_name=$(basename "$file_path")
        # Extract date from filename (format: world_id_NAME_YYYYMMDD_HHMMSS.png)
        date_part=$(echo "$file_name" | grep -oE "[0-9]{8}_[0-9]{6}" | cut -d_ -f1)
        
        # If date is newer than one week ago, download the file
        if [ "$date_part" -ge "$ONE_WEEK_AGO" ]; then
            aws s3 cp "s3://tw-timelapse/${file_path}" "${BASE_DIR}/players/" --quiet
        fi
    done

    # Repeat for tribe maps with zones of control
    aws s3 ls s3://tw-timelapse/${WORLD_ID}/top_tribes_zoc/ --recursive | grep -E "[0-9]{8}_[0-9]{6}" | while read -r line; do
        file_path=$(echo "$line" | awk '{print $4}')
        file_name=$(basename "$file_path")
        date_part=$(echo "$file_name" | grep -oE "[0-9]{8}_[0-9]{6}" | cut -d_ -f1)
        
        if [ "$date_part" -ge "$ONE_WEEK_AGO" ]; then
            aws s3 cp "s3://tw-timelapse/${file_path}" "${BASE_DIR}/tribes/zoc/" --quiet
        fi
    done

    # Repeat for tribe maps without zones of control
    aws s3 ls s3://tw-timelapse/${WORLD_ID}/top_tribes_no_zoc/ --recursive | grep -E "[0-9]{8}_[0-9]{6}" | while read -r line; do
        file_path=$(echo "$line" | awk '{print $4}')
        file_name=$(basename "$file_path")
        date_part=$(echo "$file_name" | grep -oE "[0-9]{8}_[0-9]{6}" | cut -d_ -f1)
        
        if [ "$date_part" -ge "$ONE_WEEK_AGO" ]; then
            aws s3 cp "s3://tw-timelapse/${file_path}" "${BASE_DIR}/tribes/no_zoc/" --quiet
        fi
    done

    # Count downloaded files
    PLAYER_FILE_COUNT=$(ls -1 ${BASE_DIR}/players/ 2>/dev/null | wc -l)
    TRIBE_ZOC_FILE_COUNT=$(ls -1 ${BASE_DIR}/tribes/zoc/ 2>/dev/null | wc -l)
    TRIBE_NO_ZOC_FILE_COUNT=$(ls -1 ${BASE_DIR}/tribes/no_zoc/ 2>/dev/null | wc -l)

    TOTAL_FILES=$((PLAYER_FILE_COUNT + TRIBE_ZOC_FILE_COUNT + TRIBE_NO_ZOC_FILE_COUNT))

    if [ $TOTAL_FILES -eq 0 ]; then
        echo "No files found for world ${WORLD_ID} in the past week. Skipping..."
        return 1
    fi

    echo "Found ${PLAYER_FILE_COUNT} player maps, ${TRIBE_ZOC_FILE_COUNT} tribe ZOC maps, and ${TRIBE_NO_ZOC_FILE_COUNT} tribe no-ZOC maps for world ${WORLD_ID} from the past week."

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
        ffmpeg -thread_queue_size 4096 -framerate 5 -i ${BASE_DIR}/players/%d.png -crf 16 -vf "minterpolate='mi_mode=mci:mc_mode=aobmc:vsbmc=1:fps=5',hqdn3d" -pix_fmt yuv420p ${OUTPUT_DIR}/${WORLD_ID}_player_weekly.mp4 -y -loglevel error

        # Convert MP4 to GIF for players
        ffmpeg -thread_queue_size 4096 -i ${OUTPUT_DIR}/${WORLD_ID}_player_weekly.mp4 -vf "fps=5,scale=iw/2:-1:flags=lanczos,split[s0][s1];[s0]palettegen=max_colors=256[p];[s1][p]paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle" -y ${GIF_DIR}/${WORLD_ID}_player_weekly.gif -loglevel error
    fi

    # Tribes with zones of control
    if [ -n "$(ls -A ${BASE_DIR}/tribes/zoc/ 2>/dev/null)" ]; then
        echo "Generating tribe timelapse with zones of control..."
        ffmpeg -thread_queue_size 4096 -framerate 5 -i ${BASE_DIR}/tribes/zoc/%d.png -crf 16 -vf "minterpolate='mi_mode=mci:mc_mode=aobmc:vsbmc=1:fps=5',hqdn3d" -pix_fmt yuv420p ${OUTPUT_DIR}/${WORLD_ID}_tribe_zoc_weekly.mp4 -y -loglevel error

        # Convert MP4 to GIF for tribes with zones of control
        ffmpeg -thread_queue_size 4096 -i ${OUTPUT_DIR}/${WORLD_ID}_tribe_zoc_weekly.mp4 -vf "fps=5,scale=iw/2:-1:flags=lanczos,split[s0][s1];[s0]palettegen=max_colors=256[p];[s1][p]paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle" -y ${GIF_DIR}/${WORLD_ID}_tribe_zoc_weekly.gif -loglevel error
    fi

    # Tribes without zones of control
    if [ -n "$(ls -A ${BASE_DIR}/tribes/no_zoc/ 2>/dev/null)" ]; then
        echo "Generating tribe timelapse without zones of control..."
        ffmpeg -thread_queue_size 4096 -framerate 5 -i ${BASE_DIR}/tribes/no_zoc/%d.png -crf 16 -vf "minterpolate='mi_mode=mci:mc_mode=aobmc:vsbmc=1:fps=5',hqdn3d" -pix_fmt yuv420p ${OUTPUT_DIR}/${WORLD_ID}_tribe_no_zoc_weekly.mp4 -y -loglevel error

        # Convert MP4 to GIF for tribes without zones of control
        ffmpeg -thread_queue_size 4096 -i ${OUTPUT_DIR}/${WORLD_ID}_tribe_no_zoc_weekly.mp4 -vf "fps=5,scale=iw/2:-1:flags=lanczos,split[s0][s1];[s0]palettegen=max_colors=256[p];[s1][p]paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle" -y ${GIF_DIR}/${WORLD_ID}_tribe_no_zoc_weekly.gif -loglevel error
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
echo "=== Weekly Timelapse Generation ==="
echo "This script will create timelapses for all worlds for the past week."

# Get the date from one week ago
ONE_WEEK_AGO=$(get_one_week_ago)
echo "Generating timelapses for files newer than: ${ONE_WEEK_AGO}"

# Get all available worlds
get_available_worlds
read -r -a WORLDS_TO_PROCESS <<< "$worlds"

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
    if process_world "$WORLD_ID" "$ONE_WEEK_AGO"; then
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

echo "Weekly MP4 files are in the 'outputs/' directory"
echo "Weekly GIF files are in the 'gifs/' directory"

# Optionally upload the results back to S3
read -p "Do you want to upload the results back to S3? (y/n): " UPLOAD
if [ "$UPLOAD" == "y" ]; then
    for WORLD_ID in "${SUCCESSFUL_WORLDS[@]}"; do
        echo "Uploading files for ${WORLD_ID} to S3..."
        
        # Upload videos
        if [ -d "outputs/${WORLD_ID}" ] && [ -n "$(ls -A outputs/${WORLD_ID} 2>/dev/null)" ]; then
            echo "Uploading MP4 files to S3..."
            aws s3 sync outputs/${WORLD_ID} s3://tw-timelapse/${WORLD_ID}/weekly_videos/ --quiet
        fi
        
        # Upload GIFs
        if [ -d "gifs/${WORLD_ID}" ] && [ -n "$(ls -A gifs/${WORLD_ID} 2>/dev/null)" ]; then
            echo "Uploading GIF files to S3..."
            aws s3 sync gifs/${WORLD_ID} s3://tw-timelapse/${WORLD_ID}/weekly_gifs/ --quiet
        fi
    done
    
    echo "Upload complete."
fi