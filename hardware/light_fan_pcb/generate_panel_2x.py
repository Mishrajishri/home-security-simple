import pcbnew
import os
import sys

def generate_panel(src_file, dst_file, drc_rpt_file=None):
    src = pcbnew.LoadBoard(src_file)
    dst = pcbnew.BOARD()
    dst.SetDesignSettings(src.GetDesignSettings())

    src_nets = [net.GetNetname() for net in src.GetNetsByName().values() if net.GetNetname()]

    # A4 Landscape: 297mm x 210mm
    # Each board: 100mm x 142mm
    # Copy 1 origin: (30.0, 34.0) -> Extents: [30.0..130.0, 34.0..176.0]
    # Copy 2 origin: (160.0, 34.0) -> Extents: [160.0..260.0, 34.0..176.0]
    origins = [(30.0, 34.0), (160.0, 34.0)]

    net_map_by_idx = {}
    for idx in range(1, len(origins) + 1):
        sfx = f'_{idx}' if idx > 1 else ''
        net_map_by_idx[idx] = {}
        for name in src_nets:
            new_name = name + sfx
            item = pcbnew.NETINFO_ITEM(dst, new_name)
            dst.Add(item)
            net_map_by_idx[idx][name] = item

    dst.BuildListOfNets()

    for idx, (ox, oy) in enumerate(origins, 1):
        sfx = f'_{idx}' if idx > 1 else ''
        net_map = net_map_by_idx[idx]
        
        # 1. Footprints
        for fp in src.GetFootprints():
            raw = fp.Duplicate(False)
            c = pcbnew.Cast_to_FOOTPRINT(raw)
            c.Move(pcbnew.VECTOR2I(pcbnew.FromMM(ox), pcbnew.FromMM(oy)))
            c.SetReference(fp.GetReference() + sfx)
            for pad in c.Pads():
                old_name = pad.GetNetname()
                if old_name in net_map:
                    pad.SetNet(net_map[old_name])
            dst.Add(c)
            
        # 2. Tracks
        for trk in src.GetTracks():
            raw = trk.Duplicate()
            c = pcbnew.Cast_to_PCB_TRACK(raw)
            c.Move(pcbnew.VECTOR2I(pcbnew.FromMM(ox), pcbnew.FromMM(oy)))
            old_name = trk.GetNetname()
            if old_name in net_map:
                c.SetNet(net_map[old_name])
            dst.Add(c)
            
        # 3. Drawings
        for d in src.GetDrawings():
            c = d.Duplicate()
            c.Move(pcbnew.VECTOR2I(pcbnew.FromMM(ox), pcbnew.FromMM(oy)))
            dst.Add(c)

    # Scissor cutting guide line at X = 145.0
    cut_line = pcbnew.PCB_SHAPE(dst)
    cut_line.SetShape(pcbnew.SHAPE_T_SEGMENT)
    cut_line.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(145.0), pcbnew.FromMM(20.0)))
    cut_line.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(145.0), pcbnew.FromMM(190.0)))
    cut_line.SetLayer(pcbnew.User_9)
    cut_line.SetWidth(pcbnew.FromMM(0.20))
    dst.Add(cut_line)

    txt = pcbnew.PCB_TEXT(dst)
    txt.SetText('--- CUT HERE (SCISSORS / PAPER CUTTER) ---')
    txt.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(143.0), pcbnew.FromMM(105.0)))
    txt.SetTextAngle(pcbnew.EDA_ANGLE(90, pcbnew.DEGREES_T))
    txt.SetLayer(pcbnew.Dwgs_User)
    txt.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(1.2), pcbnew.FromMM(1.2)))
    txt.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_CENTER)
    dst.Add(txt)

    dst.Save(dst_file)
    print(f"Panel successfully generated and saved to {dst_file}")

if __name__ == '__main__':
    src = '/Users/shreyansh/@nirman/hardware/light_fan_pcb/light_fan.kicad_pcb'
    dst = '/Users/shreyansh/@nirman/hardware/light_fan_pcb/light_fan_panel_2x_a4.kicad_pcb'
    generate_panel(src, dst)
