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

namespace PortfolioReport
{
    public partial class PortfolioReportForm : Form
    {
        string[] input_files = {""};
        string path_out = "";
        string pdffile_dest = "";
        string report_name = "";
        REngine engine = null;
        bool relative_returns = false;
        bool ptf_of_ptf = false;
        DateTime date_start = new DateTime(2006,1,1); 
        DateTime date_end = new DateTime(2013, 6, 30);

        public PortfolioReportForm()
        {
            InitializeComponent();

            // initialise R engine
            var envPath = Environment.GetEnvironmentVariable("PATH");
            var rBinPath = @"C:\Program Files\R\R-2.15.2\bin\i386";
            Environment.SetEnvironmentVariable("PATH", envPath + Path.PathSeparator + rBinPath);
            engine = REngine.CreateInstance("RDotNet");
            engine.Initialize();

            // do some initial R setup
            engine.Evaluate("Sys.setenv(TZ='Europe/London')");
            engine.Evaluate("library(quantmod)");
            engine.Evaluate("library(PerformanceAnalytics)");
            engine.Evaluate("print(getwd())");
            engine.Evaluate("setwd(paste0(Sys.getenv('HOME'),'/GitRepo/ApticReports/R src/'))");
            engine.Evaluate("print(getwd())");
        }

        private void button1_Click(object sender, EventArgs e)      // choose file dialog
        {
            DialogResult result = openFileDialog1.ShowDialog();
            input_files = new string[openFileDialog1.FileNames.Length];
            input_files = openFileDialog1.FileNames;

            textBox1.WordWrap = true;
            textBox1.Text = String.Join(",",input_files);
        }

        private void button2_Click(object sender, EventArgs e)      // choose output directory dialog
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

        private void button3_Click(object sender, EventArgs e)      // the Go button
        {
            progressBar1.Value = 20; 
            report_name = textBox3.Text;
            MakePtfReport(input_files, path_out, report_name);
            progressBar1.Value = 100;
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
            string target = "";
            if (pdffile_dest == "")
            {
                DialogResult result = openFileDialog2.ShowDialog();
                target = openFileDialog2.FileName;
            }
            else
            {
                target = pdffile_dest;
            }
     
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

        private void MakePtfReport(string[] input_files, string path_out, string report_name)
        {
            // make sure we start in the correct directory with a clean environment
            engine.Evaluate("rm(list=ls())");
            engine.Evaluate("gc()");
//            engine.Evaluate("setwd('C:/Users/Keiran/Documents/Backtest_Source/R')");
            engine.Evaluate("setwd(paste0(Sys.getenv('HOME'),'/GitRepo/ApticReports/R src/'))");

            // pass pnl files into R
            CharacterVector r_input_files = engine.CreateCharacterVector(input_files);
            engine.SetSymbol("filenames", r_input_files);

            // output directory
            CharacterVector r_path_out = engine.CreateCharacterVector(new string[] { path_out });
            engine.SetSymbol("path.out", r_path_out);

            // report name
            CharacterVector r_filestem = engine.CreateCharacterVector(new string[] { report_name });
            engine.SetSymbol("filestem", r_filestem);

            // pass in dates and flags
            LogicalVector r_relrtns = engine.CreateLogicalVector(new bool[] { relative_returns });
            engine.SetSymbol("rel.rtns", r_relrtns);
            ptf_of_ptf = PtfPtfCheckBox.Checked;
            LogicalVector r_ptfflag = engine.CreateLogicalVector(new bool[] { ptf_of_ptf });
            engine.SetSymbol("ptf.of.ptf", r_ptfflag);

            CharacterVector r_startEndDate = engine.CreateCharacterVector(new string[] { date_start.ToShortDateString(),date_end.ToShortDateString() });
            engine.SetSymbol("start.end.dates", r_startEndDate);


            // 2. sanity checks
            engine.Evaluate("print(rel.rtns)");
            engine.Evaluate("print(start.end.dates)");
            engine.Evaluate("print(filenames)");
            engine.Evaluate("print(path.out)");
            engine.Evaluate("print(filestem)");
            engine.Evaluate("print(paste('ptf.of.ptf = ',ptf.of.ptf,collapse=' '))");

            // 3. run R script to make daily pnl
            engine.Evaluate("source('PortfolioMakeReport.R')");

            // 4. copy pdf report to output directory
            string pdffile = report_name + ".pdf";
            string pdffile_orig = System.IO.Path.Combine(@"C:\Temp\TeX_Tmp\", pdffile);
            pdffile_dest = System.IO.Path.Combine(path_out, pdffile);
            File.Copy(pdffile_orig, pdffile_dest, true);

            // 5. copy daily and monthly pnl files to output directory
            string daily_file = report_name + "_pnl_daily.csv";
            string daily_file_orig = System.IO.Path.Combine(@"C:\Temp\TeX_Tmp\", daily_file);
            string daily_file_dest = System.IO.Path.Combine(path_out, daily_file);
            File.Copy(daily_file_orig, daily_file_dest, true);
            string monthly_file = report_name + "_pnl_monthly.csv";
            string monthly_file_orig = System.IO.Path.Combine(@"C:\Temp\TeX_Tmp\", monthly_file);
            string monthly_file_dest = System.IO.Path.Combine(path_out, monthly_file);
            File.Copy(monthly_file_orig, monthly_file_dest, true);

        
        }

        private void DoClear()
        {
            textBox1.Text = "";
            textBox2.Text = "";
            textBox3.Text = "";
            pdffile_dest = "";
            engine.Evaluate("rm(list=ls())");
            engine.Evaluate("gc()");
            progressBar1.Value = 0;
            progressBar1.Refresh();
            dateTimePicker1.Refresh();
            dateTimePicker2.Refresh();
            checkBox1.Refresh();
        }

        private string[] GetCurrencyAndDirection(string filename)
        {
            string[] lines = System.IO.File.ReadAllLines(filename);
            if (lines.Length < 3)
            {
               throw new System.IO.FileLoadException(filename + " has less than 3 lines");
            }
            // use knowledge of ninja trade files to find currency pair
            string[] fields = lines[1].Split(',');
            string [] info = new string[2];
            info[0] = fields[1].Substring(1,6);    // strip off leading $ sign

            // find direction as well
            info[1] = fields[4];

            return info;
        }

        private void textBox3_TextChanged(object sender, EventArgs e)
        {
            report_name = textBox3.Text;
        }
        
        private void dateStartChanged(object sender, EventArgs e)
        {
            this.date_start = dateTimePicker1.Value;
        }

        private void checkBox1_checkedChanged(object sender, EventArgs e)
        {
            this.relative_returns = checkBox1.Checked;
        }

        private void checkBox2_checkedChanged(object sender, EventArgs e)
        {
            this.ptf_of_ptf = PtfPtfCheckBox.Checked;
        }

        private void dateEndChanged(object sender, EventArgs e)
        {
            this.date_end = dateTimePicker2.Value;
        }

      
    }
}
