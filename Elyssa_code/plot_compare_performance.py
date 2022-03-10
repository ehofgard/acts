#!/usr/bin/env python
"""
Script to plot performance from CKF ACTS
"""
__author__ = "Elyssa Hofgard"


import ROOT
import argparse
import os,sys
import shutil

###############################################################################                                   
# Command line arguments
######################## 
def getArgumentParser():
    """ Get arguments from command line"""
    parser = argparse.ArgumentParser(description="Script to plot performance from CKF ACTS")
    parser.add_argument('-i1',
                        '--infile1',
                        dest = 'infile1',
                        help = 'input ROOT file 1')
    parser.add_argument('-i2',
                        '--infile2',
                        dest = 'infile2',
                        help = 'input ROOT file 2')
    parser.add_argument('-o',
                        '--outdir',
                        dest = 'outdir',
                        help = 'output directory for plot etc',
                        default = 'outdir')
    return parser

############################################################################### 

def main():
    options = getArgumentParser().parse_args()

    ### Make output dir
    dir_path = os.getcwd()
    out_dir = options.outdir
    infile1 = options.infile1
    infile2 = options.infile2
    path = os.path.join(dir_path, out_dir)
    if os.path.exists(path):
        shutil.rmtree(path)
    os.makedirs(path)
    os.chdir(path)

    # Read input ROOT file
    infile1 = ROOT.TFile(infile1,"READ")
    infile2 = ROOT.TFile(infile2,"READ")

    # Create TCanvas
    canvas = ROOT.TCanvas('c1','c1')
    gpad = ROOT.gPad
    k1 = list(infile1.GetListOfKeys())
    k2 = list(infile2.GetListOfKeys())
    keys_1d = ['trackeff_vs_pT','trackeff_vs_eta','trackeff_vs_phi','duplicationRate_vs_pT',
    'duplicationRate_vs_eta','duplicationRate_vs_phi','fakerate_vs_pT','fakerate_vs_eta','fakerate_vs_phi']

    # Note, need to fix this with scatterplots
    for i in range(len(k1)):
        #print(k1[i].GetClassName())
        if k1[i].GetClassName() == "TEfficiency":
            to_plot1 = k1[i].ReadObj()
            to_plot2 = k2[i].ReadObj()
            to_plot1.Draw("")
            gpad.Update()
            g1 = to_plot1.GetPaintedGraph()
            to_plot1.SetLineColor(ROOT.kBlack)
            g1.SetMinimum(0)
            g1.SetMaximum(1)
            gpad.Update()
            to_plot2.Draw("SAME")
            gpad.Update()
            g2 = to_plot2.GetPaintedGraph()
            to_plot2.SetLineColor(ROOT.kRed)
            g2.SetMinimum(0)
            g2.SetMaximum(1)
            gpad.Update()
            legend = ROOT.TLegend (0.7 ,0.2 ,0.85 ,0.35)
            legend.AddEntry(to_plot1,'Original Optuna Params')
            legend.AddEntry(to_plot2,'New Optuna Params')
            legend.SetLineWidth(0)
            legend.SetFillStyle(0)
            legend.SetTextSize(.02)
            legend.Draw('same')
            canvas.SaveAs('{0}_superimposed.pdf'.format(k1[i].GetName()))
            canvas.Clear()

if __name__ == '__main__':
    main()
