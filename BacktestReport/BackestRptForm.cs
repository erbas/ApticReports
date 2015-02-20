using System;
using System.IO;
using System.Collections.Generic;
using System.ComponentModel;
using System.Data;
using System.Diagnostics;
using System.Drawing;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Windows.Forms;
using RDotNet;

namespace BacktestReport
{
    public partial class BacktestReportForm : Form
    {
        string[] input_files = {""};
        string path_out = "";
        string time_frame = "";
        string strategy = "";
        REngine engine = null;

        public BacktestReportForm()
        {
            InitializeComponent();

            // move to directory where R scripts live
            Directory.SetCurrentDirectory(@"C:\Users\apether\Documents\GitHub\ApticReports\R src");

            // initialise R engine
            REngine.SetEnvironmentVariables();
            engine = REngine.GetInstance();

            // do some initial R setup
            engine.Evaluate("Sys.setenv(TZ='Europe/London')");
            engine.Evaluate("library(quantmod)");
            engine.Evaluate("library(PerformanceAnalytics)");
            engine.Evaluate("print(getwd())");
            //engine.Evaluate("Sys.getenv('HOME')");
            //engine.Evaluate("setwd(paste0(Sys.getenv('HOME'),'/Documents/GitHub/ApticReports/R src/'))");
            //engine.Evaluate("print(getwd())");
            engine.Evaluate("print(list.files())");
        }

        private void button1_Click(object sender, EventArgs e)      // choose file dialog
        {
            DialogResult result = openFileDialog1.ShowDialog();
            input_files = new string[openFileDialog1.FileNames.Length];
            input_files = openFileDialog1.FileNames;
            
            textBox1.Text = String.Join(",",input_files);
        }

        private void button2_Click(object sender, EventArgs e)      // choode output directory dialog
        {
            DialogResult result = folderBrowserDialog1.ShowDialog();
            path_out = folderBrowserDialog1.SelectedPath.Replace(@"\", "/"); ;
            // tidy up output path
            if (path_out.Last() != '/')
            {
                path_out = path_out + '/';
            };
            textBox2.Text = path_out;
        }

        private void button3_Click(object sender, EventArgs e)
        {
            strategy = textBox3.Text;
            time_frame = comboBox2.Text;

            int n = input_files.Length;
            int k = 1;
            foreach (string input_file in input_files)
            {
                string [] info = GetCurrencyAndDirection(input_file);
                string ccy_pair = info[0];
                string direction = info[1];
                MakeReport(input_file, ccy_pair, direction, path_out, strategy, time_frame);
                progressBar1.Increment(k * 100 / n);
                k++;
            }

        }


        private void button4_Click(object sender, EventArgs e)  // clear 
        {
            DoClear();
        }

        private void button5_Click(object sender, EventArgs e)  // quit
        {
            Application.Exit();
        }

        private void button6_Click(object sender, EventArgs e)
        {

            DialogResult result = openFileDialog2.ShowDialog(); 
            string target = openFileDialog2.FileName;
     
            try
            {
                System.Diagnostics.Process.Start(target);
            }
            catch(System.ComponentModel.Win32Exception noBrowser)
            {
                if (noBrowser.ErrorCode == -2147467259)
                    MessageBox.Show(noBrowser.Message);
            }
            catch (System.Exception other)
            {
                MessageBox.Show(other.Message);
            }
			
        }

        private void comboBox2_SelectedIndexChanged(object sender, EventArgs e)
        {
            time_frame = comboBox2.Text;
        }

        private void comboBox2_close(object sender, EventArgs e)
        {
            time_frame = comboBox2.Text;
        }

        private void textBox3_Leave(object sender, EventArgs e)
        {
            strategy = textBox3.Text;
        }

        private void MakeReport(string input_file, string ccy_pair, string direction, string path_out, string strategy, string time_frame)
        {
            // make sure we start in the correct directory with a clean slate
            engine.Evaluate("rm(list=ls())");
            engine.Evaluate("gc()");
            //engine.Evaluate("setwd('C:/Users/Keiran/Documents/Backtest_Source/R')");
            //engine.Evaluate("setwd(paste0(Sys.getenv('HOME'),'/GitRepo/ApticReports/R src/'))");
            engine.Evaluate("print(getwd())");
            // pass paths into R
            // ninja trade file 
            string filename = input_file.Replace(@"\", "/");
            CharacterVector r_input_file = engine.CreateCharacterVector(new string[] { filename });
            engine.SetSymbol("filename", r_input_file);
            // eod reval rates
            string eod_path = "C:/Users/apether/Desktop/Data History/Revaluation rates";
            CharacterVector r_eod_file = engine.CreateCharacterVector(new string[] { eod_path });
            engine.SetSymbol("path.eod", r_eod_file);
            // ccy pair
            CharacterVector r_ccy_pair = engine.CreateCharacterVector(new string[] { ccy_pair });
            engine.SetSymbol("ccy.pair", r_ccy_pair);
            // long short indicator 
            CharacterVector r_direction = engine.CreateCharacterVector(new string[] { direction });
            engine.SetSymbol("strat.dir", r_direction);
            // output directory
            CharacterVector r_path_out = engine.CreateCharacterVector(new string[] { path_out });
            engine.SetSymbol("path.out", r_path_out);
            // strategy
            CharacterVector r_strategy = engine.CreateCharacterVector(new string[] { strategy });
            engine.SetSymbol("strategy", r_strategy);
            // timeframe
            //string num_time_frame = time_frame.Split(' ')[0];
            CharacterVector r_timeframe = engine.CreateCharacterVector(new string[] { time_frame });
            engine.SetSymbol("timeframe", r_timeframe);
            // filestem
            string filestem = filename.Split('/').Last().Split('.')[0];
            CharacterVector r_filestem = engine.CreateCharacterVector(new string[] { filestem });
            engine.SetSymbol("filestem.out", r_filestem);

            // 2. sanity checks
            engine.Evaluate("print(filename)");
            engine.Evaluate("print(ccy.pair)");
            engine.Evaluate("print(strategy)");
            engine.Evaluate("print(timeframe)");
            engine.Evaluate("print(path.eod)");
            engine.Evaluate("print(path.out)");
            engine.Evaluate("print(filestem.out)"); 

            // 3. run R script to make daily pnl
            engine.Evaluate("source('BacktestMakeDaily.R')");
            
            // 4. copy pdf report to output directory
            string pdffile = filestem + ".pdf";
            string pdffile_orig = System.IO.Path.Combine(@"C:\Temp\TeX_Tmp\",pdffile );
            string pdffile_dest = System.IO.Path.Combine(path_out, pdffile);
            File.Copy(pdffile_orig, pdffile_dest, true);
                    
        }

        private void DoClear()
        {
            comboBox2.SelectedText = "";
            textBox1.Text = "";
            textBox2.Text = "";
            textBox3.Text = "";
            engine.Evaluate("rm(list=ls())");
            engine.Evaluate("gc()");
            progressBar1.Value = 0;
            progressBar1.Refresh();
        }

        private string[] GetCurrencyAndDirection(string filename)
        {
            string[] lines = System.IO.File.ReadAllLines(filename);
            if (lines.Length < 2)
            {
               throw new System.IO.FileLoadException(filename + " has less than 2 lines");
            }
            // use knowledge of ninja trade files to find currency pair
            string[] fields = lines[1].Split(',');
            string [] info = new string[2];
            info[0] = fields[1].Substring(1,6);    // strip off leading $ sign

            // find direction as well
            info[1] = fields[4];

            return info;
        }


      
    }
}
