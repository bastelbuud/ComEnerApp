#!/bin/bash
# This script processes all CR*.yaml config files in a specified directory by caslling the main.py programm
# with the appropriate parameters for year and month.

# Configuration
VENV_PATH="/Users/marcdurbach/Development/python/ComEner-calculator/.venv"  # Update this path to your virtual environment
CONFIGS_DIR="/Users/marcdurbach/Development/python/ComEner-calculator/configs"        # Update this path to your configs folder
PYTHON_SCRIPT="/Users/marcdurbach/Development/python/ComEner-calculator/analyses.py"        # Path to your Python script



# Global variables for year and month
TARGET_YEAR=""
TARGET_MONTH=""

# Function to display usage
usage() {
    echo "Usage: $0 [-y YEAR] [-m MONTH] [-h]"
    echo "  -y YEAR    : Specify year to use (optional, defaults to previous month's year)"
    echo "  -m MONTH   : Specify month to use (optional, defaults to previous month)"
    echo "  -h         : Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                    # Use previous month automatically"
    echo "  $0 -y 2024 -m 12     # Use December 2024"
    echo "  $0 -m 3              # Use March of current year if current month > 3, or previous year if current month <= 3"
    exit 1
}

# Function to parse command line arguments
parse_arguments() {
    while getopts "y:m:h" opt; do
        case $opt in
            y)
                TARGET_YEAR="$OPTARG"
                ;;
            m)
                TARGET_MONTH="$OPTARG"
                ;;
            h)
                usage
                ;;
            \?)
                echo "Invalid option: -$OPTARG" >&2
                usage
                ;;
            :)
                echo "Option -$OPTARG requires an argument." >&2
                usage
                ;;
        esac
    done
}

# Function to get previous month and year
get_previous_month_year() {
    # Get current date
    current_month=$(date +%m)
    current_year=$(date +%Y)
    
    # Calculate previous month and year
    if [ "$current_month" -eq 1 ]; then
        prev_month=12
        prev_year=$((current_year - 1))
    else
        prev_month=$((current_month - 1))
        prev_year=$current_year
    fi
    
    # Remove leading zero from month if present
    prev_month=$((10#$prev_month))
    
    echo "$prev_year $prev_month"
}

# Function to determine target year and month
determine_target_date() {
    # If both year and month are provided, use them
    if [ -n "$TARGET_YEAR" ] && [ -n "$TARGET_MONTH" ]; then
        echo "Using provided date: $TARGET_MONTH/$TARGET_YEAR" >&2
        echo "$TARGET_YEAR $TARGET_MONTH"
        return
    fi
    
    # If only month is provided, determine appropriate year
    if [ -n "$TARGET_MONTH" ] && [ -z "$TARGET_YEAR" ]; then
        current_month=$(date +%m)
        current_year=$(date +%Y)
        current_month=$((10#$current_month))
        
        if [ "$TARGET_MONTH" -lt "$current_month" ]; then
            TARGET_YEAR=$current_year
        else
            TARGET_YEAR=$((current_year - 1))
        fi
        echo "Using month $TARGET_MONTH with inferred year: $TARGET_YEAR" >&2
        echo "$TARGET_YEAR $TARGET_MONTH"
        return
    fi
    
    # If only year is provided, use previous month logic with that year
    if [ -n "$TARGET_YEAR" ] && [ -z "$TARGET_MONTH" ]; then
        current_month=$(date +%m)
        current_month=$((10#$current_month))
        
        if [ "$current_month" -eq 1 ]; then
            TARGET_MONTH=12
        else
            TARGET_MONTH=$((current_month - 1))
        fi
        echo "Using year $TARGET_YEAR with inferred previous month: $TARGET_MONTH" >&2
        echo "$TARGET_YEAR $TARGET_MONTH"
        return
    fi
    
    # Default: use automatic previous month calculation
    echo "No date parameters provided, using automatic previous month calculation" >&2
    get_previous_month_year
}

# Function to activate virtual environment
activate_venv() {
    echo "Activating virtual environment: $VENV_PATH"
    
    # Check if virtual environment exists
    if [ ! -d "$VENV_PATH" ]; then
        echo "Error: Virtual environment not found at $VENV_PATH"
        exit 1
    fi
    
    # Activate virtual environment
    source "$VENV_PATH/bin/activate"
    
    if [ $? -eq 0 ]; then
        echo "Virtual environment activated successfully"
    else
        echo "Error: Failed to activate virtual environment"
        exit 1
    fi
}

# Function to validate date parameters (only when provided)
validate_date() {
    # Only validate if parameters were actually provided
    if [ -n "$TARGET_YEAR" ]; then
        # Validate year (basic check for 4-digit year)
        if ! [[ "$TARGET_YEAR" =~ ^[0-9]{4}$ ]]; then
            echo "Error: Invalid year format. Please provide a 4-digit year."
            exit 1
        fi
    fi
    
    if [ -n "$TARGET_MONTH" ]; then
        # Validate month (1-12)
        if ! [[ "$TARGET_MONTH" =~ ^[0-9]+$ ]] || [ "$TARGET_MONTH" -lt 1 ] || [ "$TARGET_MONTH" -gt 12 ]; then
            echo "Error: Invalid month. Please provide a month between 1 and 12."
            exit 1
        fi
    fi
}

# Function to process config files
process_configs() {
    echo "Scanning for config files in: $CONFIGS_DIR"
    
    # Check if configs directory exists
    if [ ! -d "$CONFIGS_DIR" ]; then
        echo "Error: Configs directory not found at $CONFIGS_DIR"
        exit 1
    fi
    
    # Get target year and month
    read target_year target_month <<< $(determine_target_date)
    
    # Validate the date parameters if they were provided via command line
    validate_date
    
    echo "Using target date: $target_month/$target_year"
    
    # Counter for processed files
    file_count=0
    
    # Find and process CR*.yaml files
    for config_file in "$CONFIGS_DIR"/CR*.yaml; do
        # Check if files actually exist (in case no matches found)
        if [ ! -f "$config_file" ]; then
            echo "No CR*.yaml files found in $CONFIGS_DIR"
            break
        fi
        
        # Extract filename without path and extension
        filename=$(basename "$config_file" .yaml)
        
        echo "Processing config file: $filename"
        
        # Run Python script with parameters
        python "$PYTHON_SCRIPT" -g "$filename" -y "$target_year" -m "$target_month"
        
        # Check if Python script executed successfully
        if [ $? -eq 0 ]; then
            echo "Successfully processed $filename"
        else
            echo "Error: Failed to process $filename"
        fi
        
        ((file_count++))
        echo "---"
    done
    
    echo "Processed $file_count config files"
}

# Main execution
main() {
    # Parse command line arguments
    parse_arguments "$@"
    
    echo "Starting config processing script..."
    echo "Current date: $(date)"
    
    # Activate virtual environment
    activate_venv
    
    # Process config files
    process_configs
    
    echo "Script completed"
}

# Run main function with all arguments
main "$@"