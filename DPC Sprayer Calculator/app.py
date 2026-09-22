import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="DPC Sprayer Calibration Calculator",
    page_icon="🌱",
    layout="centered"
)

chemical_file = "chemical_library.xlsx"

try:
    chemicals = pd.read_excel(
        chemical_file,
        sheet_name="Chemical Library"
    )
except Exception as e:
    st.error(f"Could not load chemical library: {e}")
    st.stop()

st.title("DPC Sprayer Calibration Calculator")

st.warning(
    "Always verify the current pesticide label and application rate before mixing or spraying. "
    "The product label is the controlling legal document."
)

# -------------------------------------------------
# 1. CALIBRATE SPRAYER
# -------------------------------------------------

st.header("1. Calibrate Sprayer")

catch_unit = st.selectbox(
    "Nozzle catch unit",
    ["fl oz", "mL"]
)

catch_amount = st.number_input(
    f"Amount collected from one nozzle in 1 minute ({catch_unit})",
    min_value=0.0,
    step=0.1
)

nozzle_count = st.number_input(
    "Number of nozzles",
    min_value=1,
    step=1
)

course_distance = st.number_input(
    "Test course distance (feet)",
    min_value=1.0,
    step=1.0
)

travel_time = st.number_input(
    "Time to travel test course (seconds)",
    min_value=1.0,
    step=0.1
)

spray_width = st.number_input(
    "Actual spray width (feet)",
    min_value=0.1,
    step=0.1
)

gpa = None
mph = None

if catch_amount > 0 and travel_time > 0 and spray_width > 0:

    if catch_unit == "mL":
        catch_fl_oz = catch_amount / 29.5735
    else:
        catch_fl_oz = catch_amount

    nozzle_gpm = catch_fl_oz / 128
    distance_per_minute = course_distance * 60 / travel_time
    mph = distance_per_minute * 60 / 5280

    if mph > 15:
        st.warning(
            f"⚠️ Calculated speed is {mph:.1f} mph. "
            "That is unusually high for spraying. "
            "Check the course distance and travel time."
        )

    elif mph < 0.5:
        st.warning(
            f"⚠️ Calculated speed is {mph:.1f} mph. "
            "Check the course distance and travel time."
        )

    total_gpm = nozzle_gpm * nozzle_count

    gpa = (
        total_gpm * 43560
    ) / (
        distance_per_minute * spray_width
    )

    st.subheader("Calibration Result")

    col1, col2 = st.columns(2)

    with col1:
        st.metric(
            "Speed",
            f"{mph:.2f} mph"
        )

    with col2:
        st.metric(
            "Application Rate",
            f"{gpa:.1f} GPA"
        )

# -------------------------------------------------
# 2. TANK SIZE
# -------------------------------------------------

st.header("2. Tank Size")

tank_options = [
    50,
    75,
    100,
    150,
    200,
    250,
    300,
    500,
    "Custom"
]

tank_choice = st.selectbox(
    "Select tank size",
    tank_options
)

if tank_choice == "Custom":

    tank_gallons = st.number_input(
        "Custom tank size (gallons)",
        min_value=1.0,
        step=1.0
    )

else:
    tank_gallons = float(tank_choice)

acres_per_tank = None

if gpa and tank_gallons > 0:

    acres_per_tank = tank_gallons / gpa

    st.subheader("Tank Coverage")

    col1, col2 = st.columns(2)

    with col1:
        st.metric(
            "Tank Size",
            f"{tank_gallons:.0f} gal"
        )

    with col2:
        st.metric(
            "Acres Covered",
            f"{acres_per_tank:.2f} acres"
        )

else:

    st.info(
        "Complete the sprayer calibration above "
        "to calculate acres covered per tank."
    )

# -------------------------------------------------
# 3. SELECT CHEMICALS
# -------------------------------------------------

st.header("3. Select Chemicals")

chemical_names = (
    chemicals["Product"]
    .dropna()
    .astype(str)
    .tolist()
)

chemical_options = (
    ["Other / Not Listed"]
    + sorted(chemical_names)
)

unit_options = [
    "oz/A",
    "fl oz/A",
    "lb/A",
    "pt/A",
    "qt/A",
    "oz/100 gal",
    "fl oz/100 gal",
    "oz/gal",
    "fl oz/gal"
]


def chemical_input(slot_number):

    st.subheader(f"Chemical {slot_number}")

    selected_chemical = st.selectbox(
        f"Chemical {slot_number}",
        chemical_options,
        key=f"chemical_{slot_number}"
    )

    selected_rate = 0
    selected_units = None
    display_name = selected_chemical

    # ---------------------------------------------
    # OTHER / NOT LISTED
    # ---------------------------------------------

    if selected_chemical == "Other / Not Listed":

        display_name = st.text_input(
            "Product name",
            key=f"product_name_{slot_number}"
        )

        selected_rate = st.number_input(
            "Application rate",
            min_value=0.0,
            step=0.1,
            key=f"manual_rate_{slot_number}"
        )

        selected_units = st.selectbox(
            "Rate units",
            unit_options,
            key=f"manual_units_{slot_number}"
        )

    # ---------------------------------------------
    # LISTED CHEMICAL
    # ---------------------------------------------

    else:

        selected_row = chemicals[
            chemicals["Product"] == selected_chemical
        ].iloc[0]

        rate_low = selected_row[
            "Proposed Label Low"
        ]

        rate_high = selected_row[
            "Proposed Label High"
        ]

        selected_units = str(
            selected_row["Label Units"]
        )

        minimum_water = selected_row.get(
            "Water Required (gal/acre)",
            None
        )

        if pd.notna(minimum_water):

            minimum_water = float(minimum_water)

            st.caption(
                f"Minimum water required: "
                f"{minimum_water:.0f} GPA"
            )

            if gpa is not None and gpa < minimum_water:

                st.error(
                    f"⚠️ Current sprayer calibration is "
                    f"{gpa:.1f} GPA, but this product "
                    f"requires at least "
                    f"{minimum_water:.0f} GPA."
                )

        st.caption(
            f"Label rate range: "
            f"{rate_low} – {rate_high} "
            f"{selected_units}"
        )

        selected_rate = st.number_input(
            f"Rate to use ({selected_units})",
            min_value=float(rate_low),
            max_value=float(rate_high),
            value=float(rate_low),
            step=0.1,
            key=f"rate_{slot_number}"
        )

    # ---------------------------------------------
    # CALCULATE PRODUCT AMOUNT
    # ---------------------------------------------

    product_amount = None
    result_unit = None

    if selected_rate > 0 and selected_units:

        if "/A" in selected_units:

            if acres_per_tank is not None:

                product_amount = (
                    selected_rate
                    * acres_per_tank
                )

            else:

                st.info(
                    "Complete the sprayer calibration "
                    "to calculate this per-acre product."
                )

        elif "/100 gal" in selected_units:

            product_amount = (
                selected_rate
                * (tank_gallons / 100)
            )

        elif "/gal" in selected_units:

            product_amount = (
                selected_rate
                * tank_gallons
            )

        if product_amount is not None:

            result_unit = selected_units

            result_unit = result_unit.replace(
                "/A",
                ""
            )

            result_unit = result_unit.replace(
                "/100 gal",
                ""
            )

            result_unit = result_unit.replace(
                "/gal",
                ""
            )

    return {
        "name": display_name,
        "rate": selected_rate,
        "units": selected_units,
        "amount": product_amount,
        "result_unit": result_unit
    }


# -------------------------------------------------
# CHEMICAL 1
# -------------------------------------------------

chemical_1 = chemical_input(1)

add_chemical_2 = st.checkbox(
    "Add Chemical 2"
)

chemical_2 = None
chemical_3 = None

# -------------------------------------------------
# CHEMICAL 2
# -------------------------------------------------

if add_chemical_2:

    chemical_2 = chemical_input(2)

    add_chemical_3 = st.checkbox(
        "Add Chemical 3"
    )

    # ---------------------------------------------
    # CHEMICAL 3
    # ---------------------------------------------

    if add_chemical_3:

        chemical_3 = chemical_input(3)

# -------------------------------------------------
# 4. MIX RESULT
# -------------------------------------------------

mix_items = [
    chemical_1,
    chemical_2,
    chemical_3
]

valid_mix_items = [
    item for item in mix_items
    if item is not None
    and item["amount"] is not None
]

if valid_mix_items:

    st.header("4. Mix Result")

    col1, col2 = st.columns(2)

    with col1:
        st.metric(
            "Tank",
            f"{tank_gallons:.0f} gal"
        )

    with col2:
        if acres_per_tank is not None:
            st.metric(
                "Coverage",
                f"{acres_per_tank:.2f} acres"
            )
        else:
            st.metric(
                "Coverage",
                "Tank-volume mix"
            )

    st.divider()

    st.subheader("Add to Tank")

    for item in valid_mix_items:

        product_name = (
            item["name"]
            if item["name"]
            else "Other Product"
        )

        st.markdown(
            f"### {product_name}"
        )

        st.markdown(
            f"## {item['amount']:.2f} {item['result_unit']}"
        )

        st.caption(
            f"Rate used: {item['rate']} {item['units']}"
        )

        st.divider()

    st.warning(
        "Always verify the current product label, application rate, "
        "compatibility, and mixing instructions before spraying."
    )
# -------------------------------------------------
# 5. ADJUST GPA
# -------------------------------------------------

with st.expander("Adjust GPA"):

    if gpa is not None and mph is not None:

        st.write(
            f"Current calibration: **{gpa:.1f} GPA** "
            f"at **{mph:.2f} mph**"
        )

        target_gpa = st.number_input(
            "Target GPA",
            min_value=0.1,
            value=float(round(gpa, 1)),
            step=0.1
        )

        if target_gpa > 0:

            target_mph = (
                mph * gpa / target_gpa
            )

            st.metric(
                "Approximate target speed",
                f"{target_mph:.2f} mph"
            )

            if target_mph > 15:
                st.warning(
                    "The calculated target speed is unusually high. "
                    "A nozzle change may be more practical."
                )

            elif target_mph < 0.5:
                st.warning(
                    "The calculated target speed is unusually low. "
                    "A nozzle change may be more practical."
                )

            st.caption(
                "This assumes nozzle output, pressure, nozzle count, "
                "and spray width stay the same."
            )

    else:

        st.info(
            "Complete the sprayer calibration above to use the GPA adjustment tool."
        )