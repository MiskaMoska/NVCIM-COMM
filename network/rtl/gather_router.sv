`include "params.svh"

module gather_router #(
    parameter   string rt_file_list[`CN] = '{(`CN){"/mnt/f/git/NVCIM-COMM/behavior_model/config/gather_rt_0_0_4"}}
)(
    input       wire                            clk,
    input       wire                            rstn, 

    //west port,channel id = 1
    input       wire                            west_valid_i,
    input       wire        [`DW-1:0]           west_data_i,
    output      wire                            west_ready_o,

    output      wire                            west_valid_o,
    output      wire        [`DW-1:0]           west_data_o,
    input       wire                            west_ready_i,

    //east port,channel id = 2
    input       wire                            east_valid_i,
    input       wire        [`DW-1:0]           east_data_i,
    output      wire                            east_ready_o,

    output      wire                            east_valid_o,
    output      wire        [`DW-1:0]           east_data_o,
    input       wire                            east_ready_i,

    //north port,channel id = 3
    input       wire                            north_valid_i,
    input       wire        [`DW-1:0]           north_data_i,
    output      wire                            north_ready_o,

    output      wire                            north_valid_o,
    output      wire        [`DW-1:0]           north_data_o,
    input       wire                            north_ready_i,

    //south port,channel id = 4
    input       wire                            south_valid_i,
    input       wire        [`DW-1:0]           south_data_i,
    output      wire                            south_ready_o,

    output      wire                            south_valid_o,
    output      wire        [`DW-1:0]           south_data_o,
    input       wire                            south_ready_i,

    //local port,channel id = 0
    input       wire                            local_valid_i,
    input       wire        [`DW-1:0]           local_data_i,
    output      wire                            local_ready_o,

    output      wire                            local_valid_o,
    output      wire        [`DW-1:0]           local_data_o,
    input       wire                            local_ready_i
);

wire    [4:0]       selVCfromVC0,reqVCfromVC0,selOutVCtoVC0;
wire    [4:0]       selVCfromVC1,reqVCfromVC1,selOutVCtoVC1;
wire    [4:0]       selVCfromVC2,reqVCfromVC2,selOutVCtoVC2;
wire    [4:0]       selVCfromVC3,reqVCfromVC3,selOutVCtoVC3;
wire    [4:0]       selVCfromVC4,reqVCfromVC4,selOutVCtoVC4;

wire    [`DW-1:0]   data_from_vc0,data_to_vc0;
wire    [`DW-1:0]   data_from_vc1,data_to_vc1;
wire    [`DW-1:0]   data_from_vc2,data_to_vc2;
wire    [`DW-1:0]   data_from_vc3,data_to_vc3;
wire    [`DW-1:0]   data_from_vc4,data_to_vc4;
wire    [`DW-1:0]   data_from_vc5,data_to_vc5;

wire    [4:0]       valid_from,valid_to,ready_from,ready_to;
wire    [4:0]       outVCAvailable,VCgranted,outVCAvailableReset;

gather_input_stage #(
    .rt_file                  (rt_file_list[1])
)input_stage_west(
    .clk                      (clk),
    .rstn                     (rstn),
    .valid_i                  (west_valid_i),
    .data_i                   (west_data_i),
    .ready_o                  (west_ready_o),
    .reqVC                    (reqVCfromVC1),
    .selOutVC                 (selOutVCtoVC1),
    .VCgranted                (VCgranted[1]),
    .selXBVC                  (selVCfromVC1),
    .valid_o                  (valid_from[1]),
    .data_o                   (data_from_vc1),
    .ready_i                  (ready_to[1])
);

gather_input_stage #( 
    .rt_file                  (rt_file_list[2])
)input_stage_east(
    .clk                      (clk),
    .rstn                     (rstn),
    .valid_i                  (east_valid_i),
    .data_i                   (east_data_i),
    .ready_o                  (east_ready_o),
    .reqVC                    (reqVCfromVC2),
    .selOutVC                 (selOutVCtoVC2),
    .VCgranted                (VCgranted[2]),
    .selXBVC                  (selVCfromVC2),
    .valid_o                  (valid_from[2]),
    .data_o                   (data_from_vc2),
    .ready_i                  (ready_to[2])
);

gather_input_stage #(
    .rt_file                  (rt_file_list[3])
)input_stage_north(
    .clk                      (clk),
    .rstn                     (rstn),
    .valid_i                  (north_valid_i),
    .data_i                   (north_data_i),
    .ready_o                  (north_ready_o),
    .reqVC                    (reqVCfromVC3),
    .selOutVC                 (selOutVCtoVC3),
    .VCgranted                (VCgranted[3]),
    .selXBVC                  (selVCfromVC3),
    .valid_o                  (valid_from[3]),
    .data_o                   (data_from_vc3),
    .ready_i                  (ready_to[3])
);

gather_input_stage #(
    .rt_file                  (rt_file_list[4])
)input_stage_south(
    .clk                      (clk),
    .rstn                     (rstn),
    .valid_i                  (south_valid_i),
    .data_i                   (south_data_i),
    .ready_o                  (south_ready_o),
    .reqVC                    (reqVCfromVC4),
    .selOutVC                 (selOutVCtoVC4),
    .VCgranted                (VCgranted[4]),
    .selXBVC                  (selVCfromVC4),
    .valid_o                  (valid_from[4]),
    .data_o                   (data_from_vc4),
    .ready_i                  (ready_to[4])
);

gather_input_stage #(
    .rt_file                  (rt_file_list[0])
)input_stage_local(
    .clk                      (clk),
    .rstn                     (rstn),
    .valid_i                  (local_valid_i),
    .data_i                   (local_data_i),
    .ready_o                  (local_ready_o),
    .reqVC                    (reqVCfromVC0),
    .selOutVC                 (selOutVCtoVC0),
    .VCgranted                (VCgranted[0]),
    .selXBVC                  (selVCfromVC0),
    .valid_o                  (valid_from[0]),
    .data_o                   (data_from_vc0),
    .ready_i                  (ready_to[0])
);

gather_output_stage output_stage_vc0(
    .clk                      (clk),
    .rstn                     (rstn),
    .flit_type                (data_to_vc0[`DW-1:`DW-2]),
    .flit_fire                (valid_to[0] & ready_from[0]),
    .outVCAvailableReset      (outVCAvailableReset[0]),
    .outVCAvailable           (outVCAvailable[0])
);

gather_output_stage output_stage_vc1(
    .clk                      (clk),
    .rstn                     (rstn),
    .flit_type                (data_to_vc1[`DW-1:`DW-2]),
    .flit_fire                (valid_to[1] & ready_from[1]),
    .outVCAvailableReset      (outVCAvailableReset[1]),
    .outVCAvailable           (outVCAvailable[1])
);

gather_output_stage output_stage_vc2(
    .clk                      (clk),
    .rstn                     (rstn),
    .flit_type                (data_to_vc2[`DW-1:`DW-2]),
    .flit_fire                (valid_to[2] & ready_from[2]),
    .outVCAvailableReset      (outVCAvailableReset[2]),
    .outVCAvailable           (outVCAvailable[2])
);

gather_output_stage output_stage_vc3(
    .clk                      (clk),
    .rstn                     (rstn),
    .flit_type                (data_to_vc3[`DW-1:`DW-2]),
    .flit_fire                (valid_to[3] & ready_from[3]),
    .outVCAvailableReset      (outVCAvailableReset[3]),
    .outVCAvailable           (outVCAvailable[3])
);

gather_output_stage output_stage_vc4(
    .clk                      (clk),
    .rstn                     (rstn),
    .flit_type                (data_to_vc4[`DW-1:`DW-2]),
    .flit_fire                (valid_to[4] & ready_from[4]),
    .outVCAvailableReset      (outVCAvailableReset[4]),
    .outVCAvailable           (outVCAvailable[4])
);

gather_vc_allocator vc_allocator(
    .clk                      (clk),
    .rstn                     (rstn),
    .reqVCfromVC0             (reqVCfromVC0),
    .reqVCfromVC1             (reqVCfromVC1),
    .reqVCfromVC2             (reqVCfromVC2),
    .reqVCfromVC3             (reqVCfromVC3),
    .reqVCfromVC4             (reqVCfromVC4),
    .outVCAvailable           (outVCAvailable),
    .selOutVCtoVC0            (selOutVCtoVC0),
    .selOutVCtoVC1            (selOutVCtoVC1),
    .selOutVCtoVC2            (selOutVCtoVC2),
    .selOutVCtoVC3            (selOutVCtoVC3),
    .selOutVCtoVC4            (selOutVCtoVC4),
    .VCgranted                (VCgranted),
    .outVCAvailableReset      (outVCAvailableReset)
);

gather_crossbar crossbar(
    .selVCfromVC0             (selVCfromVC0),
    .selVCfromVC1             (selVCfromVC1),
    .selVCfromVC2             (selVCfromVC2),
    .selVCfromVC3             (selVCfromVC3),
    .selVCfromVC4             (selVCfromVC4),
    .data_in_vc0              (data_from_vc0),
    .data_in_vc1              (data_from_vc1),
    .data_in_vc2              (data_from_vc2),
    .data_in_vc3              (data_from_vc3),
    .data_in_vc4              (data_from_vc4),
    .data_out_vc0             (data_to_vc0),
    .data_out_vc1             (data_to_vc1),
    .data_out_vc2             (data_to_vc2),
    .data_out_vc3             (data_to_vc3),
    .data_out_vc4             (data_to_vc4),
    .valid_in                 (valid_from),
    .valid_out                (valid_to),
    .ready_in                 (ready_from),
    .ready_out                (ready_to)
);

assign west_data_o   = data_to_vc1;
assign east_data_o   = data_to_vc2;
assign north_data_o  = data_to_vc3;
assign south_data_o  = data_to_vc4;
assign local_data_o  = data_to_vc0;

assign west_valid_o  = valid_to[1];
assign east_valid_o  = valid_to[2];
assign north_valid_o = valid_to[3];
assign south_valid_o = valid_to[4];
assign local_valid_o = valid_to[0];

assign ready_from[1] = west_ready_i;
assign ready_from[2] = east_ready_i;
assign ready_from[3] = north_ready_i;
assign ready_from[4] = south_ready_i;
assign ready_from[0] = local_ready_i;

endmodule