# T0.3 OpenROAD command probe.  Usage: openroad -no_init -no_splash -exit probe_openroad.tcl
# Prints one line per command: PROBE <cmd> <available 0/1> <flags found>/<flags wanted>
set cmds {
  rtl_macro_placer {}
  macro_placement {}
  place_macro {}
  global_placement {-skip_initial_place -incremental -routability_driven -timing_driven -overflow}
  detailed_placement {}
  check_placement {}
  estimate_parasitics {-placement -global_routing}
  report_wns {}
  report_tns {}
  global_route {-congestion_iterations -congestion_report_file}
  set_global_routing_region_adjustment {}
  set_global_routing_layer_adjustment {}
  detailed_route {}
  write_db {}
  read_db {}
  write_guides {}
  rcx::extract_parasitics {}
  extract_parasitics {}
  write_def {}
  read_def {}
}
puts "PROBE_VERSION [ord::openroad_version]"
foreach {c flags} $cmds {
  set have [expr {[llength [info commands $c]] > 0 || [llength [info commands ::$c]] > 0}]
  set help ""
  # OpenROAD/OpenSTA keep each command's argument spec in the Tcl array sta::cmd_args
  if {$have && [info exists sta::cmd_args($c)]} { set help $sta::cmd_args($c) }
  set found {}
  foreach f $flags { if {[string first $f $help] >= 0} { lappend found $f } }
  puts "PROBE $c $have [join $found ,]/[join $flags ,]"
  if {$help ne ""} { puts "HELP_BEGIN $c\n$help\nHELP_END $c" }
}
puts "PROBE_DONE"
