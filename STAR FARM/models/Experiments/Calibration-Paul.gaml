/**
* Name: Calibration
* Author: Patrick Taillandier 
* Tags: 
*/ 
   
 
model Calibration
 
import "../Global.gaml"

  
global  {   
	 
	 float fitness;  
     
     map<Indicator, float> indicators; 
    
    string calibration_output <- "Calibration/calibration_result.csv";
    
    string province <- DONG_THAP_OLD;
    
    
   
   map<string, list<list<float>>> historical_yields <- [
    
    // DONG THAP: High and stable yields (Freshwater control zone)
   DONG_THAP_OLD:: [
        [ 6.80, 7.20, 7.32, 7.25, 7.18, 7.30, 7.35], // Spring (Win.-Spr.)
        [5.70, 5.60, 6.21, 6.28, 6.34, 6.40, 6.42], // Autumn (Sum.-Aut.)
        [6.10, 6.10, 6.15, 6.20, 6.25, 6.30, 6.31]  // Winter (Aut.-Win.)
    ],
    
    // LONG AN: Acidic soils (Plaine des Joncs) limiting potential despite being in freshwater
    LONG_AN:: [
        [ 6.15, 6.68, 6.75, 6.65, 6.62, 6.80, 6.85], // Spring (Win.-Spr.)
        [4.80, 5.05, 5.15, 5.20, 5.25, 5.40, 5.45], // Autumn (Sum.-Aut.)
        [ 4.90, 5.02, 5.10, 5.25, 5.30, 5.45, 5.52]  // Winter (Aut.-Win.)
    ],

    // TRA VINH: Coastal Zone (Vulnerable to sea-level dry-season peaks)
    TRA_VINH:: [
        [4.82, 6.24, 6.45, 6.20, 5.40, 6.65, 6.72], // Spring (Win.-Spr.)
        [ 5.15, 5.21, 5.35, 5.28, 5.35, 5.50, 5.55], // Autumn (Sum.-Aut.)
        [4.61, 5.14, 5.25, 5.35, 5.50, 5.60, 5.65]  // Winter (Aut.-Win.)
    ],

    // BEN TRE: Extreme Estuary Zone (Highly impacted by dry-season saline peaks)
    BEN_TRE:: [
        [2.15, 4.95, 5.10, 4.80, 3.45, 5.25, 5.35], // Spring (Win.-Spr.)
        [4.20, 4.65, 4.75, 4.70, 4.80, 4.90, 4.95], // Autumn (Sum.-Aut.)
        [ 4.10, 4.48, 4.55, 4.60, 4.70, 4.80, 4.85]  // Winter (Aut.-Win.)
    ]
];


    bool fitness_computed <- false;
    action compute_fitness() {
    	if not fitness_computed {
	    	fitness <- 0.0; 
	    	string error_ <- "";
	    	float sum_weight <- 0.0;
	    	loop ind over: indicators.keys {
	    		float err <-  ind.compute_error();
	    		error_ <-error_ + err + ",";
	    		fitness <- fitness + (err * indicators[ind]); 
	    		sum_weight <- sum_weight + indicators[ind];
	    	}
	    	
	    	string result <- "" + int(self)+ ","+ seed+","+ rue_efficiency_factor+ ","+pest_infection_prob+","+ pest_daily_increment 
	    	     +","+toxicity_per_straw_unit+ ","+  solar_rad_threshold +","+  max_diffuse_bonus   +","+ max_light_limit +","+steepness_factor
	    		 +","+max_water_capacity +","+ lateral_leakage_coefficient +","+ water_excess_coefficient;
	    	result <- result + ","+ error_+fitness+"\n";
	    	if (save_calibration_results) {
	    		save result format: "text" to: calibration_output rewrite: false;
	    	
	    	} else {
	    		write "\n" + result;
	    	}
	    	fitness_computed <- true; 
    	}
    }
   	
   
	action prepare_indicators() {
		ask Avg_yield {
			store_values <- true;
			list<list<float>> data <- historical_yields[province];
			list<float> spring_2016_2023 <- data[0];
			list<float> autumn_2016_2023 <- data[1];
			list<float> winter_2016_2023 <- data[2] ;
			loop i from: 0 to: length(spring_2016_2023) -1  {
				//conversion -> t/ha
				observed_values_per_seasons << spring_2016_2023[i];
				observed_values_per_seasons << autumn_2016_2023[i];
				observed_values_per_seasons << winter_2016_2023[i];
				
			}
			
			indicators[self] <- 5.0;
			
		}
		ask Avg_pesticide_applications {
			store_values <- true;
			observed_values_avg_seasons << 6;
			observed_values_avg_seasons << 5.5;
			observed_values_avg_seasons << 5;
			indicators[self] <- 1.0;
			non_representative_years <- [2016,2020];
		}
		
		ask Avg_fertilizer_usage {
			store_values <- true;
			observed_values_avg_seasons << 132.0;
			observed_values_avg_seasons << 108.0;
			observed_values_avg_seasons << 84.0;
			indicators[self] <- 1.0;
			non_representative_years <- [2016,2020];
		}
	
		ask Avg_irrigation_usage {
			store_values <- true;
			//conversion m3/ha -> mm/ha
			observed_values_avg_seasons << (8186 / 10.0);
			observed_values_avg_seasons << (5830 / 10.0);
			observed_values_avg_seasons << (2204 / 10.0);
			indicators[self] <- 1.0;
			non_representative_years <- [2016,2020];
		}
		
		
	
	}
	
		
}


experiment check_result type: batch until: end_of_sim repeat: 1 keep_seed: true {
	method exploration 
	with: ( [["write_calibration_result"::true]]);
	


	init { 
		gama.pref_parallel_simulations_all <- false;
		gama.pref_parallel_threads <- 4; 
		mode_batch <- true;
		save_results <- false; 
		write_results <- false;
		write_calibration_result <- true;     
		save_calibration_results <- false; 
    
		use_weather_generator <- false;
		innovation_diffusion_model <- NONE;
		possible_practices <- [BAU_3S::1.0];
   		starting_date <- date([2015,1,1]) add_days (day_start_of_year -1);
   		ending_date <-  date([2023,1,1]);
	}
}   


experiment single_evaluation type: batch until: end_of_sim repeat: 1 keep_seed: true parent: generic_exp  {
	parameter "absolute_csv_path" var: calibration_output;
	parameter "mode_batch" var: mode_batch <- true;
	parameter "save_calibration_results" var: save_calibration_results <- true;
	
	parameter rue_efficiency_factor var: rue_efficiency_factor;
	parameter pest_infection_prob var: pest_infection_prob;
	parameter pest_daily_increment var: pest_daily_increment;
	parameter toxicity_per_straw_unit var: toxicity_per_straw_unit;
	parameter solar_rad_threshold var: solar_rad_threshold;
	parameter max_diffuse_bonus var: max_diffuse_bonus;
	parameter max_light_limit var: max_light_limit;
	parameter steepness_factor var: steepness_factor;
	parameter max_water_capacity var: max_water_capacity;
	parameter lateral_leakage_coefficient var: lateral_leakage_coefficient;
	parameter water_excess_coefficient var: water_excess_coefficient;
	
	method exploration 
	with: ( [
		["save_calibration_results"::true],
		["mode_batch"::true],
		["save_results"::false],
		["write_results"::false]
	]);
	
	init {
		gama.pref_parallel_simulations_all <- false;
		gama.pref_parallel_threads <- 4;
		mode_batch <- true;
		save_results <- false; 
		write_results <- false;
		write_calibration_result <- false;     
		save_calibration_results <- true;
 
		use_weather_generator <- false;
		innovation_diffusion_model <- NONE;
		possible_practices <- [BAU_3S::1.0];
		
		starting_date <- date([2015,1,1]) add_days (day_start_of_year -1);
   		ending_date <-  date([2024,1,1]);

		// We no longer write the header here, Python handles it!
	}
}