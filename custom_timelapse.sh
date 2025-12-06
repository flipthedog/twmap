#!/bin/bash

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "AWS CLI is not installed. Please install it first."
    exit 1
fi

# Check for ffmpeg
if ! command -v ffmpeg &> /dev/null; then
    echo "ffmpeg is not installed. Please install it first."
    exit 1
fi

# Function to process a specific S3 folder
process_folder() {
    local S3_PATH=$1
    local FOLDER_NAME=$(basename "$S3_PATH")
    local WORLD_ID=$(echo "$S3_PATH" | cut -d'/' -f1)
    
    echo "===== Processing folder: ${S3_PATH} ====="

    # Define directories
    BASE_DIR="images/${WORLD_ID}/${FOLDER_NAME}"
    OUTPUT_DIR="outputs/${WORLD_ID}"
    GIF_DIR="gifs/${WORLD_ID}"

    # Create required directories
    mkdir -p ${BASE_DIR}
    mkdir -p ${OUTPUT_DIR}
    mkdir -p ${GIF_DIR}

    # Clear image folder before syncing
    echo "Clearing image folder..."
    rm -rf ${BASE_DIR}/*

    # Download all images from the specified S3 folder
    echo "Downloading map images from s3://tw-timelapse/${S3_PATH}..."
    aws s3 sync "s3://tw-timelapse/${S3_PATH}/" "${BASE_DIR}/" --quiet

    # Count downloaded files
    FILE_COUNT=$(ls -1 ${BASE_DIR}/ 2>/dev/null | grep -c "\.png$")

    if [ $FILE_COUNT -eq 0 ]; then
        echo "No images found in s3://tw-timelapse/${S3_PATH}. Skipping..."
        return 1
    fi

    echo "Downloaded ${FILE_COUNT} images from the specified folder."

    # Rename files to sequential numbers for ffmpeg
    echo "Preparing files for processing..."
    
    # Rename all PNG files sequentially
    if [ -n "$(ls -A ${BASE_DIR}/ 2>/dev/null)" ]; then
        pushd ${BASE_DIR}/ > /dev/null
        ls -1 *.png 2>/dev/null | sort | awk '{printf "mv \"%s\" \"%d.png\"\n", $0, NR}' | bash
        popd > /dev/null
    else
        echo "No images found in ${BASE_DIR}/"
        return 1
    fi

    # Process files
    echo "Generating timelapse..."

    # Create timers
    start_time=$(date +%s)

    # Generate MP4
    OUTPUT_FILENAME="${WORLD_ID}_${FOLDER_NAME}_timelapse.mp4"
    echo "Generating MP4 timelapse..."
    ffmpeg -thread_queue_size 4096 -framerate 5 -i ${BASE_DIR}/%d.png -crf 16 \
        -vf "minterpolate='mi_mode=mci:mc_mode=aobmc:vsbmc=1:fps=5',hqdn3d" \
        -pix_fmt yuv420p "${OUTPUT_DIR}/${OUTPUT_FILENAME}" -y -loglevel error

    # Generate GIF
    GIF_FILENAME="${WORLD_ID}_${FOLDER_NAME}_timelapse.gif"
    echo "Generating GIF timelapse..."
    ffmpeg -thread_queue_size 4096 -i "${OUTPUT_DIR}/${OUTPUT_FILENAME}" \
        -vf "fps=5,scale=iw/2:-1:flags=lanczos,split[s0][s1];[s0]palettegen=max_colors=256[p];[s1][p]paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle" \
        -y "${GIF_DIR}/${GIF_FILENAME}" -loglevel error

    # Calculate elapsed time
    end_time=$(date +%s)
    elapsed_time=$((end_time - start_time))

    echo "Completed processing for ${S3_PATH}."
    echo "Time taken: ${elapsed_time} seconds"
    echo ""
    
    return 0
}

# Main script starts here
echo "=== Custom Folder Timelapse Generation ==="

# Ask for S3 folder path
read -p "Enter the S3 folder path (e.g., en146/specific_tribes/my_special_tribe): " S3_PATH

if [ -z "$S3_PATH" ]; then
    echo "No folder path provided. Exiting."
    exit 1
fi

# Verify the folder exists
echo "Checking if the folder exists..."
if ! aws s3 ls "s3://tw-timelapse/${S3_PATH}/" &>/dev/null; then
    echo "Folder s3://tw-timelapse/${S3_PATH}/ does not exist or is empty. Exiting."
    exit 1
fi

echo "Will create a timelapse for: s3://tw-timelapse/${S3_PATH}/"
read -p "Do you want to continue? (y/n): " CONFIRM

if [ "$CONFIRM" != "y" ]; then
    echo "Operation cancelled. Exiting."
    exit 0
fi

# Process the folder
if process_folder "$S3_PATH"; then
    echo "Timelapse created successfully."
    
    # Get filenames for display
    WORLD_ID=$(echo "$S3_PATH" | cut -d'/' -f1)
    FOLDER_NAME=$(basename "$S3_PATH")
    OUTPUT_FILENAME="${WORLD_ID}_${FOLDER_NAME}_timelapse.mp4"
    GIF_FILENAME="${WORLD_ID}_${FOLDER_NAME}_timelapse.gif"
    
    echo "MP4 file: outputs/${WORLD_ID}/${OUTPUT_FILENAME}"
    echo "GIF file: gifs/${WORLD_ID}/${GIF_FILENAME}"
    
    # Optionally upload the results back to S3
    read -p "Do you want to upload the results back to S3? (y/n): " UPLOAD
    if [ "$UPLOAD" == "y" ]; then
        echo "Uploading files to S3..."
        
        # Upload MP4
        aws s3 cp "outputs/${WORLD_ID}/${OUTPUT_FILENAME}" "s3://tw-timelapse/${WORLD_ID}/custom_videos/${FOLDER_NAME}_timelapse.mp4" --quiet
        
        # Upload GIF
        aws s3 cp "gifs/${WORLD_ID}/${GIF_FILENAME}" "s3://tw-timelapse/${WORLD_ID}/custom_gifs/${FOLDER_NAME}_timelapse.gif" --quiet
        
        echo "Upload complete."
        echo "Files are available at:"
        echo "s3://tw-timelapse/${WORLD_ID}/custom_videos/${FOLDER_NAME}_timelapse.mp4"
        echo "s3://tw-timelapse/${WORLD_ID}/custom_gifs/${FOLDER_NAME}_timelapse.gif"
    fi
else
    echo "Failed to create timelapse."
fi