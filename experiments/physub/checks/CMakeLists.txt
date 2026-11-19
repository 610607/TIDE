# Small-grid checks quoted in README entries; see checks/README.md. Each builds against the
# current sources; none is run by ctest.
foreach(chk chk_trial chk_trial_fill chk_tail chk_tail_extra chk_cut chk_cut_pop chk_cut_short
        chk_shift chk_probe chk_born chk_wall chk_fillscan)
  add_executable(${chk} ${chk}.cpp)
  target_link_libraries(${chk} PRIVATE physub)
  target_include_directories(${chk} PRIVATE ${PROJECT_SOURCE_DIR}/apps)
  target_compile_options(${chk} PRIVATE ${PHYSUB_WARNINGS})
endforeach()
