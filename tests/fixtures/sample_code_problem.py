"""
MRPL Engineering Calculation - Pipe Wall Thickness Estimation
Using ASME B31.3 Process Piping Code

Task: Calculate minimum required pipe wall thickness for crude oil line.
Given:
  - Design pressure P = 24 bar = 2.4 MPa
  - Pipe outer diameter D = 168.3 mm (6-inch NPS)
  - Material: A106 Gr. B carbon steel
  - Design temperature: 350degC
  - Allowable stress S at 350degC = 103.4 MPa (from ASME tables)
  - Corrosion allowance c = 3.0 mm
  - Quality factor E = 1.0 (seamless)
  - Y coefficient = 0.4 (ferritic steel, T < 482degC)

Formula (ASME B31.3, Clause 304.1.2):
  t_min = (P × D) / (2 × (S×E + P×Y)) + c
"""

import math

def calculate_pipe_wall_thickness(P_bar, D_mm, S_MPa, E=1.0, Y=0.4, c_mm=3.0):
    """
    ASME B31.3 minimum pipe wall thickness calculation.
    
    Args:
        P_bar  : Design pressure in bar
        D_mm   : Outer diameter in mm
        S_MPa  : Allowable stress at design temperature in MPa
        E      : Quality factor (1.0 for seamless)
        Y      : Y-coefficient (temp dependent, 0.4 for <482degC ferritic)
        c_mm   : Corrosion allowance in mm
    
    Returns:
        dict with all intermediate values and results
    """
    P_MPa = P_bar / 10.0       # convert bar to MPa
    
    # ASME B31.3 Formula
    t_pressure = (P_MPa * D_mm) / (2 * (S_MPa * E + P_MPa * Y))
    t_min = t_pressure + c_mm   # add corrosion allowance
    
    # Select next standard wall thickness (schedule)
    # Common wall thicknesses for 6" pipe in mm
    schedules = {
        "Sch 10S": 3.40, "Sch 20":  4.78, "Sch 30":  5.56,
        "Sch 40 (Std)": 7.11, "Sch 60": 8.74, "Sch 80 (XH)": 10.97,
        "Sch 120": 14.27, "Sch 160": 18.26, "Sch XXH": 21.95
    }
    selected_sch = None
    selected_t   = None
    for sch, t in schedules.items():
        if t >= t_min:
            selected_sch = sch
            selected_t   = t
            break
    
    # Pressure at selected wall thickness (back-calculation)
    if selected_t:
        t_eff = selected_t - c_mm   # effective thickness after corrosion
        P_max = (2 * S_MPa * E * t_eff) / (D_mm - 2 * Y * t_eff)
        P_max_bar = P_max * 10
    else:
        P_max_bar = None
    
    return {
        "design_pressure_bar": P_bar,
        "design_pressure_MPa": round(P_MPa, 3),
        "outer_diameter_mm": D_mm,
        "allowable_stress_MPa": S_MPa,
        "quality_factor_E": E,
        "Y_coefficient": Y,
        "corrosion_allowance_mm": c_mm,
        "t_pressure_mm": round(t_pressure, 3),
        "t_minimum_required_mm": round(t_min, 3),
        "selected_schedule": selected_sch,
        "selected_wall_thickness_mm": selected_t,
        "max_allowable_pressure_bar": round(P_max_bar, 2) if P_max_bar else None,
        "design_factor": round(P_max_bar / P_bar, 2) if P_max_bar else None,
    }


def print_report(result):
    print("=" * 60)
    print("  ASME B31.3 PIPE WALL THICKNESS CALCULATION")
    print("  MRPL - CDU Unit 4 - Crude Feed Line")
    print("=" * 60)
    print(f"  Design Pressure      : {result['design_pressure_bar']} bar ({result['design_pressure_MPa']} MPa)")
    print(f"  Outer Diameter       : {result['outer_diameter_mm']} mm (6-inch NPS)")
    print(f"  Allowable Stress     : {result['allowable_stress_MPa']} MPa @ 350degC")
    print(f"  Quality Factor (E)   : {result['quality_factor_E']}")
    print(f"  Y Coefficient        : {result['Y_coefficient']}")
    print(f"  Corrosion Allowance  : {result['corrosion_allowance_mm']} mm")
    print("-" * 60)
    print(f"  Pressure Term (t)    : {result['t_pressure_mm']} mm")
    print(f"  Minimum t required   : {result['t_minimum_required_mm']} mm")
    print("-" * 60)
    print(f"  Selected Schedule    : {result['selected_schedule']}")
    print(f"  Selected Wall t      : {result['selected_wall_thickness_mm']} mm")
    print(f"  Max Allowable Press  : {result['max_allowable_pressure_bar']} bar")
    print(f"  Design Factor        : {result['design_factor']}x")
    print("=" * 60)
    print("  ✓ COMPLIANT with ASME B31.3" if result['design_factor'] and result['design_factor'] >= 1.0 else "  ✗ NON-COMPLIANT")
    print("=" * 60)


if __name__ == "__main__":
    result = calculate_pipe_wall_thickness(
        P_bar=24,        # design pressure
        D_mm=168.3,      # 6-inch NPS OD
        S_MPa=103.4,     # A106 Gr.B @ 350degC
        E=1.0,           # seamless
        Y=0.4,           # ferritic, <482degC
        c_mm=3.0,        # corrosion allowance
    )
    print_report(result)
