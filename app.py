from flask import Flask, request, render_template, jsonify
import pandas as pd

app = Flask(__name__)

# Define the load_csv function
def load_csv(file_path):
    try:
        df = pd.read_csv(file_path)
        df.columns = df.columns.str.strip()  # Strip any leading/trailing whitespace from column names
        # Normalize string columns by stripping any leading/trailing spaces
        for col in df.columns:
            if df[col].dtype == 'object':  # Check if the column contains string data
                df[col] = df[col].str.strip()
        # Convert the 'Cost' column to numeric (handling commas and other non-numeric characters)
        if 'Cost' in df.columns:
            df['Cost'] = pd.to_numeric(df['Cost'].replace(r'[\$,]', '', regex=True), errors='coerce')
        return df
    except Exception as e:
        print(f"Error loading '{file_path}': {e}")
        return pd.DataFrame()  # Return an empty DataFrame if there's an error

# Load all CSV files
azure_df = load_csv('azure_cost.csv')
aws_df = load_csv('aws_cost.csv')
gcp_df = load_csv('google_cost.csv')
aws_config_df = load_csv('awsconfig.csv')  # Load the new AWS config file

def get_unique_values(df, column):
    # Get unique values from a specific dataframe
    unique_values = set()
    if column in df.columns:
        if df[column].dtype in ['int64', 'float64']:
            unique_values.update(df[column].dropna().astype(int).unique())
        else:
            unique_values.update(df[column].dropna().unique())
    return sorted(unique_values)

def get_cost(df, region, os, type, category, vcpu, ram, ssd):
    result = df[
        (df['Region'] == region) &
        (df['OS'] == os) &
        (df['Type'] == type) &
        (df['Category'] == category) &
        (df['vCPU'] == vcpu) &
        (df['RAM'] == ram) &
        (df['SSD'] == ssd)
    ]
    if not result.empty:
        return result['Cost'].values[0], result['Instance Type'].values[0]
    return None, None  # Return None if configuration is not found

@app.route('/', methods=['GET', 'POST'])
def index():
    # Get unique values for the main form
    region_options = get_unique_values(azure_df, 'Region')
    os_options = get_unique_values(azure_df, 'OS')
    type_options = get_unique_values(azure_df, 'Type')
    category_options = get_unique_values(azure_df, 'Category')
    vcpu_options = get_unique_values(azure_df, 'vCPU')
    ram_options = get_unique_values(azure_df, 'RAM')
    ssd_options = get_unique_values(azure_df, 'SSD')

    # Get unique values for the AWS config form (only from awsconfig.csv)
    aws_config_regions = get_unique_values(aws_config_df, 'Region')
    aws_config_tenancies = get_unique_values(aws_config_df, 'Tenancy')
    aws_config_os = get_unique_values(aws_config_df, 'OS')
    aws_config_vcpus = get_unique_values(aws_config_df, 'vCPU')
    aws_config_rams = get_unique_values(aws_config_df, 'RAM')
    aws_config_ssds = get_unique_values(aws_config_df, 'SSD')

    # Initialize variables
    azure_cost = aws_cost = gcp_cost = None
    azure_instance_type = aws_instance_type = gcp_instance_type = None
    selected_resources = False
    region = os = type = category = vcpu = ram = ssd = quantity = month = None
    error_message = None

    if request.method == 'POST':
        try:
            region = request.form['region']
            os = request.form['os']
            type = request.form['type']
            category = request.form['category']
            vcpu = int(request.form['vcpu'])
            ram = int(request.form['ram'])
            ssd = int(request.form['ssd'])
            quantity = int(request.form['quantity'])
            month = int(request.form['month'])

            # Get costs and instance types from all vendors
            azure_cost, azure_instance_type = get_cost(azure_df, region, os, type, category, vcpu, ram, ssd)
            aws_cost, aws_instance_type = get_cost(aws_df, region, os, type, category, vcpu, ram, ssd)
            gcp_cost, gcp_instance_type = get_cost(gcp_df, region, os, type, category, vcpu, ram, ssd)

            # Convert cost values to floats (if they are not already)
            azure_cost = float(azure_cost) if azure_cost is not None else None
            aws_cost = float(aws_cost) if aws_cost is not None else None
            gcp_cost = float(gcp_cost) if gcp_cost is not None else None

            selected_resources = True  # Set to True to display the Selected Resources Container
        except ValueError:
            error_message = "Invalid input. Please select valid options."

    return render_template(
        'index.html',
        region_options=region_options,
        os_options=os_options,
        type_options=type_options,
        category_options=category_options,
        vcpu_options=vcpu_options,
        ram_options=ram_options,
        ssd_options=ssd_options,
        aws_config_regions=aws_config_regions,
        aws_config_tenancies=aws_config_tenancies,
        aws_config_os=aws_config_os,
        aws_config_vcpus=aws_config_vcpus,
        aws_config_rams=aws_config_rams,
        aws_config_ssds=aws_config_ssds,
        azure_cost=azure_cost,
        aws_cost=aws_cost,
        gcp_cost=gcp_cost,
        azure_instance_type=azure_instance_type,
        aws_instance_type=aws_instance_type,
        gcp_instance_type=gcp_instance_type,
        selected_resources=selected_resources,
        region=region,
        os=os,
        type=type,
        category=category,
        vcpu=vcpu,
        ram=ram,
        ssd=ssd,
        quantity=quantity if quantity is not None else 1,
        month=month if month is not None else 1,
        error_message=error_message
    )

@app.route('/calculate-aws-config', methods=['POST'])
def calculate_aws_config():
    data = request.get_json()
    region = data.get('aws-region')
    tenancy = data.get('aws-tenancy')
    os = data.get('aws-os')
    vcpu = int(data.get('aws-vcpu'))
    ram = int(data.get('aws-ram'))
    ssd = int(data.get('aws-ssd'))

    # Debugging: Print input data
    print(f"Input Data - Region: {region}, Tenancy: {tenancy}, OS: {os}, vCPU: {vcpu}, RAM: {ram}, SSD: {ssd}")

    # Find the matching row in awsconfig.csv
    result = aws_config_df[
        (aws_config_df['Region'] == region) &
        (aws_config_df['Tenancy'] == tenancy) &
        (aws_config_df['OS'] == os) &
        (aws_config_df['vCPU'] == vcpu) &
        (aws_config_df['RAM'] == ram) &
        (aws_config_df['SSD'] == ssd)
    ]

    # Debugging: Print matching rows
    print(f"Matching Rows:\n{result}")

    if not result.empty:
        cost = result['Cost'].values[0]
        print(f"Calculated Cost: {cost}")  # Debugging: Print the calculated cost
        return jsonify({
            'cost': cost,
            'message': '',
            'aws_region': region,
            'aws_tenancy': tenancy,
            'aws_os': os,
            'aws_vcpu': vcpu,
            'aws_ram': ram,
            'aws_ssd': ssd
        })
    else:
        print("No matching configuration found.")  # Debugging: Print if no match is found
        return jsonify({
            'cost': 0,
            'message': 'Configuration not available',
            'aws_region': region,
            'aws_tenancy': tenancy,
            'aws_os': os,
            'aws_vcpu': vcpu,
            'aws_ram': ram,
            'aws_ssd': ssd
        })

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=5000)