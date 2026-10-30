"""Render already admitted A105 stoichiometric cells without source rereading."""
from collections.abc import Mapping


def is_row(value):
    return (isinstance(value, Mapping)
        and value.get('evaluation_scope') == 'source_soluble_product_stoichiometric_balance'
        and isinstance(value.get('component'), str)
        and isinstance(value.get('sheet_ref'), str))


def render_received(parts, rows, *, section, table):
    if not rows:
        return
    first = rows[0]
    section(parts, 'CcCdP Figure 2D source experiment', table(('Meaning', 'Source-bound value'), [
        ('Panel', first['panel']), ('Time (min)', first['time_minutes']),
        ('Assayed molecule', first['assayed_molecule']),
        ('Construct in workbook', first['construct_status']),
        ('Expression host in workbook', first['expression_host']),
        ('Initial G2 basis', 'Data!B52 equals nominal Metadata!F5; distinct measured time-zero mean not established'),
        ('Initial G3–G6 and Pi entries', 'Data!D52,F52,H52,J52,N52 print zero; measurement and detection limits unestablished'),
        ('Nominal donor (mM)', first['reaction_conditions']['nominal_donor_mM']),
        ('Nominal G2 (mM)', first['reaction_conditions']['nominal_acceptor_mM']),
        ('Enzyme (U/mL)', first['reaction_conditions']['enzyme_U_per_mL']),
        ('MES (mM)', first['reaction_conditions']['MES_mM']),
        ('pH', first['reaction_conditions']['pH']),
        ('Temperature (°C)', first['reaction_conditions']['temperature_C']),
        ('Pi premise', first['one_pi_per_transfer_premise']),
        ('HPLC calibration check', 'selected G2–G6 means within source-stated ranges; recovery and curve error unmeasured'),
        ('Pi readout', 'separate colorimetric assay'),
        ('Reported spread basis', first['reported_sd_basis']),
        ('Matched no-enzyme arm', first['matched_no_enzyme_arm']),
        ('Independent protein preparations', first['independent_preparation_count']),
        ('Joint covariance', first['joint_covariance']),
        ('Molecule-specific attribution', first['molecule_specific_attribution'])]))
    section(parts, 'Requested soluble-product balance numerical components', table(
        ('Component', 'Value', 'Unit', 'Meaning', 'Origin', 'Source cell(s)'),
        [(r['component'], r['value'], r['unit'], r['meaning'], r['origin'],
          ', '.join(r['source_cell_addresses'])) for r in rows]))
    section(parts, 'Dependence and inference limits',
        'G2-loss and Pi accounting reuse G3–G6. W/Pi is descriptive soluble-product accounting under the sourced one-Pi-per-transfer model; it is not an assay-validity multiplier. Pi−W is an inferred remainder, not measured insoluble product. W/nominal donor is the same dependent expression as (Pi/nominal donor) × (W/Pi). Source SDs do not supply ratio SD, SE or confidence intervals without covariance. No matched no-enzyme correction, independent preparation count, molecule-specific attribution or annotation credit is supplied.')


__all__ = ['is_row', 'render_received']
