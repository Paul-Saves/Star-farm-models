model test_write

global {
	string calibration_output <- "default.csv";
	init {
		save "HELLO FROM GAMA" format: "text" to: calibration_output rewrite: false;
	}
}

experiment test_exp type: gui {
	parameter "absolute_csv_path" var: calibration_output;
}