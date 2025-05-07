import pandas as pd
import numpy as np
from datetime import datetime, date
from io import BytesIO
from ipywidgets import (
    FileUpload, Button, VBox, Output, Label, SelectMultiple, HBox,
    FloatSlider, Dropdown, Text, Checkbox
)
from IPython.display import display, clear_output
from pypfopt.efficient_frontier import EfficientFrontier
from pypfopt import objective_functions
import copy

output_all = Output()
df_global = None
selected_assets = []
sector_mapper = {}
sector_constraint_widgets = {}
expected_return_inputs = {}
constraint_rows = []
constraint_inputs = []

# Step Tracking
current_step = 0

upload = FileUpload(accept=".xlsx", multiple=False)

def log_returns(df):
    return np.log(df / df.shift(1)).dropna()

def ewma_covariance_matrix(X, alpha):
    T, D = X.shape
    cov = np.zeros((D, D))
    for tt in range(T):
        x_t = X[tt, :]
        if tt == 0:
            cov = x_t[:, np.newaxis] @ x_t[np.newaxis, :]
        else:
            cov = alpha * cov + (1 - alpha) * x_t[:, np.newaxis] @ x_t[np.newaxis, :]
    return cov

def show_asset_selector():
    with output_all:
        clear_output()
        asset_select = SelectMultiple(description="Assets:", options=df_global.columns.tolist(), rows=10)
        continue_btn = Button(description="➡ Define Sectors", button_style="primary")
        
        def proceed(change):
            global selected_assets
            selected_assets = list(asset_select.value)
            if not selected_assets:
                print("⚠️ Please select at least one asset.")
                return
            show_expected_return_inputs()

        continue_btn.on_click(proceed)
        display(VBox([
            Label("📊 Step 2: Select assets:"),
            asset_select,
            continue_btn
        ]))

def show_expected_return_inputs():
    with output_all:
        clear_output()
        global expected_return_inputs
        expected_return_inputs = {}
        rows = []

        for name in selected_assets:
            label = Label(value=name, layout={'width': '200px'})
            er_input = Text(placeholder='Expected Return (e.g. 0.05)', layout={'width': '100px'})
            expected_return_inputs[name] = er_input
            rows.append(HBox([label, er_input]))

        next_btn = Button(description="➡ Define Sectors", button_style="primary")
        
        def proceed(change):
            for asset, widget in expected_return_inputs.items():
                try:
                    float(widget.value)
                except ValueError:
                    print(f"❌ Invalid input for {asset}. Please enter a numeric value.")
                    return
            show_expected_return_summary()
        
        next_btn.on_click(proceed)
        
        display(VBox([
            Label("📈 Step 3: Enter expected returns:"),
            VBox(rows),
            next_btn
        ]))

def show_expected_return_summary():
    with output_all:
        clear_output()
        summary = pd.DataFrame.from_dict(
            {k: [float(v.value)] for k, v in expected_return_inputs.items()},
            orient='index',
            columns=['Expected Return']
        )
        print("✅ Expected Returns Summary:")
        display(summary)
        
        next_btn = Button(description="➡ Define Sectors", button_style="primary")
        next_btn.on_click(lambda change: show_sector_mapping())
        display(next_btn)

def show_sector_mapping():
    with output_all:
        clear_output()
        mapping_widgets = {}
        rows = []

        for asset in selected_assets:
            label = Label(value=asset, layout={"width": "200px"})
            dropdown = Dropdown(
                options=["Equities", "Corporate Bonds", "High Yield", "Euro Government Core", "Cash"],
                layout={"width": "200px"}
            )
            mapping_widgets[asset] = dropdown
            rows.append(HBox([label, dropdown]))

        next_btn = Button(description="➡ Set Sector Constraints", button_style="primary")

        def proceed_mapping(change):
            global sector_mapper
            sector_mapper = {a: w.value for a, w in mapping_widgets.items()}
            show_sector_mapping_summary()

        next_btn.on_click(proceed_mapping)
        display(VBox([
            Label("🏷 Step 4: Assign sectors to assets:"),
            VBox(rows),
            next_btn
        ]))

def show_sector_mapping_summary():
    with output_all:
        clear_output()
        summary = pd.DataFrame.from_dict(sector_mapper, orient='index', columns=['Sector'])
        print("✅ Sector Mapping Summary:")
        display(summary)
        
        next_btn = Button(description="➡ Set Sector Constraints", button_style="primary")
        next_btn.on_click(lambda change: show_additional_constraints())
        display(next_btn)

def show_additional_constraints():
    with output_all:
        clear_output()
        constraint_rows.clear()
        constraint_inputs.clear()
        
        for _ in range(3):  # up to 3 constraints
            asset1_dd = Dropdown(options=selected_assets, description="Asset A")
            relation_dd = Dropdown(options=["==", "<=", ">="], description="Relation")
            asset2_dd = Dropdown(options=selected_assets + ["Value"], description="Asset B/Value")
            value_input = Text(placeholder="0.1")
            
            constraint_inputs.append((asset1_dd, relation_dd, asset2_dd, value_input))
            row = HBox([asset1_dd, relation_dd, asset2_dd, value_input])
            constraint_rows.append(row)
        
        next_btn = Button(description="📋 Review and Confirm", button_style="primary")
        next_btn.on_click(lambda change: show_review_and_confirm())
        
        display(VBox([
            Label("🧩 Additional Constraints (A <= B or A == 0.1):"),
            VBox(constraint_rows),
            next_btn
        ]))

def show_review_and_confirm():
    with output_all:
        clear_output()
        print("🔎 Final Review and Confirm")
        
        print("✅ Assets Selected:", selected_assets)
        print("\n✅ Expected Returns:")
        display(pd.DataFrame.from_dict({k: [float(v.value)] for k, v in expected_return_inputs.items()},
                                       orient='index', columns=['Expected Return']))
        
        print("\n✅ Sector Mapping:")
        display(pd.DataFrame.from_dict(sector_mapper, orient='index', columns=['Sector']))
        
        print("\n✅ Constraints:")
        for asset1, relation, asset2, value in constraint_inputs:
            print(f"{asset1.value} {relation.value} {asset2.value if asset2.value != 'Value' else value.value}")

        # Add "Run Optimization" button
        run_btn = Button(description="🚀 Run Optimization", button_style="success")
        display(run_btn)

upload.observe(lambda change: show_asset_selector(), names="value")
display(VBox([
    Label("📥 Step 1: Upload Excel file (sheet: PyData):"),
    upload,
    output_all
]))
