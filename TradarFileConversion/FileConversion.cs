using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Data;
using System.Drawing;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Windows.Forms;

namespace TradarFileConversion
{
    public partial class FileConversion : Form
    {
        String[] input_files = new String[] {""};
        String path_out = "";
        String destination = "";

        public FileConversion()
        {
            InitializeComponent();
            progressBar1.Style = ProgressBarStyle.Continuous;
            progressBar1.Maximum = 100;
            progressBar1.Value = 0;
        }

        private void ButtonFile_Click(object sender, EventArgs e)           // select NT7 trade files to convert 
        {
            DialogResult result = openFileDialog1.ShowDialog();
            input_files = new string[openFileDialog1.FileNames.Length];
            input_files = openFileDialog1.FileNames;

            textBox1.WordWrap = true;
            textBox1.Text = String.Join(",", input_files);

        }

        private void ButtonFolder_Click(object sender, EventArgs e)         // select destination folder
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

        private void comboBox1_SelectedIndexChanged(object sender, EventArgs e)
        {
            destination = comboBox1.Text;
        }

/*        private void comboBox1_Close(object sender, EventArgs e)
        {
            destination = comboBox1.Text;
        }
*/

        private void ButtonQuit_Click(object sender, EventArgs e)
        {
            Application.Exit();
        }


        private void ButtonGo_Click(object sender, EventArgs e)         // do the file conversion
        {
            destination = comboBox1.Text;
            double inc = 100/input_files.Length;
            int n = 1;
            foreach (string filename in input_files) 
            {
                DoNT7toTradar(filename, path_out);
                progressBar1.Value = (int)(n * inc);
                progressBar1.Update();
                n++;
            }

        }

        private void DoNT7toTradar(string filename, string path_out)
        {

            string nt7filename = System.IO.Path.GetFileNameWithoutExtension(filename);

          //  Trade-#,Instrument,Account,Strategy,Market pos.,Quantity,Entry price,Exit price,Entry time,Exit time,Entry name,Exit name,Profit,Cum. profit,Commission,MAE,MFE,ETD,Bars,
            Dictionary<string, int> nt7 = new Dictionary<string, int>();

            nt7["Trade Number"] = 0;
            nt7["Instrument"] = 1;
            nt7["Account"] = 2;
            nt7["Strategy"] = 3;
            nt7["Market pos."] = 4;
            nt7["Quantity"] = 5;
            nt7["Entry price"] = 6;
            nt7["Exit price"] = 7;
            nt7["Entry time"] = 8;
            nt7["Exit time"] = 9;
            nt7["Entry name"] = 10;
            nt7["Exit name"] = 11;
            nt7["Profit"] = 12;

            // need to reverse position for closing trades
            Dictionary<string, string> nt7_close = new Dictionary<string, string>();
            nt7_close.Add("Long", "Sell");
            nt7_close.Add("Short", "Buy");

            // translate NT7 trade types into tradar types
            Dictionary<string, string> trade_type = new Dictionary<string, string>();
            trade_type.Add("Long", "Purchase");
            trade_type.Add("Short", "Short");
            trade_type.Add("Sell", "Sell");
            trade_type.Add("Buy", "Cover");
            
            // use a hash of the full filename with path to get an integer reference linking buys and sells
            string filename_hash = Math.Abs(filename.GetHashCode()).ToString(); 

            // parse full path to discern strategy information
            string [] path_pieces = filename.Split(new char [] {System.IO.Path.PathSeparator, ' ', '_'} );
           
            string entry_type = "";
            if (filename.Contains("CIT"))
            {
                entry_type = "CIT";
            }
            else if (filename.Contains("MR"))
            {
                entry_type = "MR";
            }
            else if (filename.Contains("Trend"))
            {
                entry_type = "Trend";
            }

            string [] n7filename_pieces = nt7filename.Split(' ');
            string entry_type_reference = n7filename_pieces[0];
            string time_frame = n7filename_pieces[2];
            string strategy_direction = n7filename_pieces[3].Split('_')[0];

            string exit_type = "";
            if (n7filename_pieces[5].Contains('x'))
            {
                exit_type = "Ratio"; // +n7filename_pieces.Last();
            }
            else if (n7filename_pieces[5].Split('_')[0] == "b")
            {
                exit_type = "TSL";
            }
            else if (n7filename_pieces[5].Split('_')[0] == "a")
            {
                exit_type = "ACAP";
            }
            else if (n7filename_pieces[5].Split('_')[0] == "ab")
            {
                exit_type = "ACAP TSL";
            }



            // open the output file
            // define headings for output file
            string tradar_headers = "Trade Type, Instrument, Entry Type, Entry Type Reference, TimeFrame, Strategy Direction, Exit Type, Amount, Price, Trade Date, RefNum, Book";

            string tradar_trade_filename = System.IO.Path.Combine(new string[] { path_out, nt7filename + "_tradar.csv" });
            System.IO.StreamWriter tradar_trade_file = new System.IO.StreamWriter(tradar_trade_filename);
            tradar_trade_file.WriteLine(tradar_headers);
            
            // debug
            Console.WriteLine("about to process");

            foreach (string line in System.IO.File.ReadLines(filename))
            {
                string[] s = line.Split(',');
                if (s[0] == "Trade-#" || s[1] == "Instrument")
                {
                    continue;  // skip the first line
                }
                string security_identifier = s[nt7["Instrument"]].Trim(new char[] {'$'});
                string trade_ref = filename_hash + '_' + s[nt7["Trade Number"]];
                string strategy = nt7filename;

                string s_tradar_1 = String.Join(",", new string [] {   
                                                trade_type[s[nt7["Market pos."]]], 
                                                security_identifier, 
                                                entry_type,
                                                entry_type_reference,
                                                time_frame,
                                                strategy_direction,
                                                exit_type,
                                                s[nt7["Quantity"]],
                                                s[nt7["Entry price"]],
                                                s[nt7["Entry time"]],
                                                trade_ref,
                                                destination
                                            });

                string s_tradar_2 = String.Join(",", new string [] {   
                                                trade_type[nt7_close[s[nt7["Market pos."]]]], 
                                                security_identifier, 
                                                entry_type,
                                                entry_type_reference,
                                                time_frame,
                                                strategy_direction,
                                                exit_type,
                                                s[nt7["Quantity"]],
                                                s[nt7["Exit price"]],
                                                s[nt7["Exit time"]],
                                                trade_ref,
                                                destination
                                            });


                //Console.WriteLine(s_tradar_1);
                //Console.WriteLine(s_tradar_2);
                tradar_trade_file.WriteLine(s_tradar_1);
                tradar_trade_file.WriteLine(s_tradar_2);
            }

            // debug
            Console.WriteLine("done processing");

            tradar_trade_file.Close();

        }


    }
}
